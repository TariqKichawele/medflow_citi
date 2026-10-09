set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

usage() {
  cat <<'EOF'
Usage: bin/seed.sh [--reset] [--yes]

Load demo data into the database named by DATABASE_URL.
A second run leaves existing rows in place.

  --reset   Delete hospitals, users, equipment, work orders, and service
            reports, then load the demo data again. Asks for confirmation.
  --yes     With --reset, skip the confirmation prompt.
  -h, --help
            Show this message.

Required environment (already exported, or set in backend/.env):
  DATABASE_URL    Postgres URL for the database to seed.

Optional environment:
  SEED_FORCE=1    Allow seeding a database host that is not local.
EOF
}

RESET=0
YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset) RESET=1 ;;
    --yes) YES=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

database_url_was_set=0
seed_force_was_set=0
saved_database_url="${DATABASE_URL-}"
saved_seed_force="${SEED_FORCE-}"
if [[ -n "${DATABASE_URL+x}" ]]; then
  database_url_was_set=1
fi
if [[ -n "${SEED_FORCE+x}" ]]; then
  seed_force_was_set=1
fi

if [[ -f "$BACKEND/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$BACKEND/.env"
  set +a
fi

if [[ "$database_url_was_set" -eq 1 ]]; then
  DATABASE_URL="$saved_database_url"
  export DATABASE_URL
fi
if [[ "$seed_force_was_set" -eq 1 ]]; then
  SEED_FORCE="$saved_seed_force"
  export SEED_FORCE
fi
unset saved_database_url saved_seed_force

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "error: DATABASE_URL is not set. Add it to backend/.env or export it before running bin/seed.sh." >&2
  exit 1
fi

if [[ -f "$BACKEND/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$BACKEND/.venv/bin/activate"
elif [[ -f "$BACKEND/.venv/Scripts/activate" ]]; then
  # shellcheck disable=SC1091
  source "$BACKEND/.venv/Scripts/activate"
else
  echo "error: virtual environment missing. Run bin/setup.sh first." >&2
  exit 1
fi

cd "$BACKEND"

echo "==> Checking database connection"
python -m app.seed --check

if [[ "$RESET" -eq 1 && "$YES" -ne 1 ]]; then
  if [[ ! -t 0 ]]; then
    echo "error: --reset needs confirmation. Re-run with --yes to skip the prompt." >&2
    exit 1
  fi
  echo "Warning: --reset deletes hospitals, users, equipment, work orders, and service reports, then reloads demo data."
  printf "Type yes to continue: "
  if ! read -r reply; then
    echo
    echo "error: reset cancelled. Re-run with --yes to skip the prompt." >&2
    exit 1
  fi
  reply="$(printf '%s' "$reply" | tr -d '[:space:]')"
  if [[ "$reply" != "yes" && "$reply" != "YES" && "$reply" != "y" && "$reply" != "Y" ]]; then
    echo
    echo "error: reset cancelled." >&2
    exit 1
  fi
fi

echo "==> Applying migrations"
alembic upgrade head

if [[ "$RESET" -eq 1 ]]; then
  python -m app.seed --reset
else
  python -m app.seed
fi
