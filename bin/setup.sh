set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml" --project-directory "$ROOT")

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "error: prerequisite missing: ${name}" >&2
    exit 1
  fi
}

echo "==> Checking prerequisites"
require_command python3
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "error: prerequisite python3 3.10 or newer is required" >&2
  exit 1
fi

require_command docker
if ! docker compose version >/dev/null 2>&1; then
  echo "error: prerequisite missing: docker compose" >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "error: prerequisite not running: Docker daemon" >&2
  exit 1
fi

if [[ -f "$ROOT/frontend/package.json" ]]; then
  require_command node
  require_command npm
  if ! node -e 'const major = Number(process.versions.node.split(".")[0]); process.exit(major >= 20 ? 0 : 1)'; then
    echo "error: prerequisite node 20 or newer is required" >&2
    exit 1
  fi
fi

if [[ -d "$BACKEND/.venv" ]]; then
  echo "==> Virtual environment already exists"
else
  echo "==> Creating Python virtual environment"
  python3 -m venv "$BACKEND/.venv"
fi

if [[ -f "$BACKEND/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$BACKEND/.venv/bin/activate"
  ACTIVATE_HINT="source backend/.venv/bin/activate"
elif [[ -f "$BACKEND/.venv/Scripts/activate" ]]; then
  echo "==> Using the Windows virtual environment (Scripts/activate)"
  # shellcheck disable=SC1091
  source "$BACKEND/.venv/Scripts/activate"
  ACTIVATE_HINT="source backend/.venv/Scripts/activate"
else
  echo "error: virtual environment activate script not found." >&2
  echo "Expected backend/.venv/bin/activate on macOS and Linux, or backend/.venv/Scripts/activate on Windows." >&2
  exit 1
fi

python -m pip install --upgrade pip
python -m pip install -r "$BACKEND/requirements.txt"

if [[ -f "$BACKEND/.env" ]]; then
  echo "==> Keeping existing backend/.env"
else
  if [[ ! -f "$BACKEND/.env.example" ]]; then
    echo "error: backend/.env.example is missing, so backend/.env was not created." >&2
    exit 1
  fi
  env_tmp="$(mktemp "${TMPDIR:-/tmp}/medflow-env.XXXXXX")"
  trap 'rm -f "$env_tmp"' EXIT
  cp "$BACKEND/.env.example" "$env_tmp"
  MEDFLOW_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  export MEDFLOW_JWT_SECRET
  set +e
  database_url_action="$(
    cd "$BACKEND"
    python - "$env_tmp" <<'PY'
import os
import sys
from pathlib import Path

from app.config import Settings

path = Path(sys.argv[1])
secret = os.environ["MEDFLOW_JWT_SECRET"]
default_url = Settings.model_fields["database_url"].default
if not isinstance(default_url, str):
    default_url = ""
default_url = default_url.strip()


def quote_dotenv(value: str) -> str:
    if "'" not in value and "\n" not in value and "\r" not in value:
        return "'" + value + "'"
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
        .replace("`", "\\`")
    )
    return f'"{escaped}"'


def unquote_dotenv(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


lines = path.read_text(encoding="utf-8").splitlines()
replaced_secret = False
wrote_database_url = False
saw_database_url = False
updated = []
for raw in lines:
    stripped = raw.strip()
    exported = stripped.startswith("export ")
    body = stripped[len("export ") :].strip() if exported else stripped
    if body.startswith("JWT_SECRET="):
        prefix = "export JWT_SECRET=" if exported else "JWT_SECRET="
        updated.append(f"{prefix}{secret}")
        replaced_secret = True
        continue
    if body.startswith("DATABASE_URL="):
        saw_database_url = True
        current = unquote_dotenv(body.split("=", 1)[1])
        if current:
            updated.append(raw)
            continue
        if not default_url:
            raise SystemExit(
                "error: DATABASE_URL is blank in backend/.env and the application has no local database default."
            )
        prefix = "export DATABASE_URL=" if exported else "DATABASE_URL="
        updated.append(f"{prefix}{quote_dotenv(default_url)}")
        wrote_database_url = True
        continue
    updated.append(raw)
if not replaced_secret:
    updated.append(f"JWT_SECRET={secret}")
if not saw_database_url:
    if not default_url:
        raise SystemExit(
            "error: DATABASE_URL is missing from backend/.env and the application has no local database default."
        )
    updated.append(f"DATABASE_URL={quote_dotenv(default_url)}")
    wrote_database_url = True
path.write_text("\n".join(updated) + "\n", encoding="utf-8")
print("filled" if wrote_database_url else "kept")
PY
  )"
  env_status=$?
  set -e
  unset MEDFLOW_JWT_SECRET
  if [[ "$env_status" -ne 0 ]]; then
    rm -f "$env_tmp"
    trap - EXIT
    exit "$env_status"
  fi
  mv "$env_tmp" "$BACKEND/.env"
  chmod 600 "$BACKEND/.env"
  trap - EXIT
  echo "==> Created backend/.env and generated JWT_SECRET"
  if [[ "$database_url_action" == "filled" ]]; then
    echo "==> Set DATABASE_URL in backend/.env from the application default"
  fi
fi

echo "==> Ensuring Postgres is running"
"${COMPOSE[@]}" up -d

echo "==> Waiting for Postgres to become healthy"
healthy=0
for _ in $(seq 1 30); do
  status="$("${COMPOSE[@]}" ps --format '{{.Health}} {{.Status}}' postgres 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)"
  # Match the word healthy. "unhealthy" must not count.
  case "$status" in
    healthy*|*\(healthy\)*) healthy=1 ;;
  esac
  if [[ "$healthy" -eq 1 ]]; then
    break
  fi
  sleep 1
done
if [[ "$healthy" -ne 1 ]]; then
  echo "error: Postgres did not become healthy." >&2
  exit 1
fi

echo "==> Running migrations"
(
  cd "$BACKEND"
  alembic upgrade head
)

if [[ -f "$ROOT/frontend/package.json" ]]; then
  echo "==> Installing frontend packages"
  (cd "$ROOT/frontend" && npm install)
fi

echo "==> Setup complete. From the repository root, start the API with:"
echo "    ${ACTIVATE_HINT} && cd backend && uvicorn app.main:app --reload"
if ! grep -Eq '^[[:space:]]*(export[[:space:]]+)?DATABASE_URL=[^[:space:]#]' "$BACKEND/.env"; then
  echo "==> DATABASE_URL is empty in backend/.env. Set it before running bin/seed.sh."
fi
