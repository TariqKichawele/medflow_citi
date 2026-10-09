# MedFlow

Centralized clinical equipment command center for Halcyon Health Systems. This repository ships the FastAPI backend, local Docker PostgreSQL database, and a React (Vite) + Material UI command center. The same app deploys to Lambda, RDS, S3, and CloudFront.

## Local setup

Requires Python 3.10+, Docker with the Compose plugin (daemon running), and Node.js 20+.

```bash
chmod +x bin/setup.sh bin/seed.sh
./bin/setup.sh
./bin/seed.sh
```

Both scripts resolve paths from their own location, so they can be run from any working directory. They exit non-zero when a step fails. Neither script contains database credentials.

### `bin/setup.sh`

Checks that `python3`, `docker`, `docker compose`, and (when `frontend/package.json` is present) `node` and `npm` are available before it changes anything. If one is missing or the Docker daemon is stopped, it prints that name and stops.

On a first run it creates `backend/.venv`, installs Python dependencies, copies `backend/.env.example` to `backend/.env`, generates `JWT_SECRET`, and, when `DATABASE_URL` is blank, writes the application's local database default into that file without printing the value. It then starts Postgres 16, runs Alembic migrations, and installs frontend packages. The activate script is `backend/.venv/bin/activate` on macOS and Linux, and `backend/.venv/Scripts/activate` on Windows.

Running it again keeps the existing virtual environment and never overwrites `backend/.env`.

### `bin/seed.sh`

Reads the database from the environment. Values already exported win; anything unset is filled from `backend/.env`.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | Postgres URL. A new `backend/.env` receives the local default from setup when this is blank. The script exits immediately if this is missing, and exits before writing if that database cannot be reached. |
| `SEED_FORCE` | no | Set to `1` to allow a database host that is not local. |

```bash
./bin/seed.sh                 # create tables if needed and load demo data
./bin/seed.sh                 # second run: leave the rows unchanged
./bin/seed.sh --reset         # ask first, then delete and reload demo data
./bin/seed.sh --reset --yes   # delete and reload without the prompt
```

`--reset` removes hospitals, users, equipment, work orders, and service reports. Declining the prompt, or running it without a terminal and without `--yes`, exits non-zero and changes nothing. Demo data includes low-charge devices, a technician assigned outside the device's hospital, a hospital over the maintenance threshold, and a work order in each status.

Start the API:

```bash
source backend/.venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

- Health: [http://localhost:8000/health](http://localhost:8000/health)
- OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

Start the UI (in a second terminal):

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The command center is at [http://localhost:5173](http://localhost:5173). Leave `VITE_API_BASE_URL` empty so Vite proxies `/api` and `/uploads` to the API on port 8000.

### UI by role

| Screen | Clinical admin | Field technician | Auditor |
| --- | --- | --- | --- |
| Dashboard | yes | yes | yes |
| Equipment / hospitals / work orders | full CRUD | read scoped data; status + report upload on assigned orders | read-only |
| Users | full CRUD (deactivate instead of hard delete) | hidden | read-only |

List grids request one page at a time. `page` and `page_size` (maximum 100) select the page, `search`, `status`, and `facility_id` narrow equipment and work orders, and `sort_by` / `sort_dir` order the SQL result. An unknown sort field or a page size above 100 returns 422. The search box is debounced so a keystroke does not become a request.

## Demo accounts

Shared password: `Medflow123!`

| Email | Role |
| --- | --- |
| `admin@halcyon.health` | Clinical admin |
| `supervisor.east@halcyon.health` | Clinical admin (Northeast supervisor) |
| `supervisor.west@halcyon.health` | Clinical admin (West supervisor) |
| `auditor@halcyon.health` | Auditor (read-only) |
| `tech.metro@halcyon.health` | Field technician (Metro General) |
| `tech.riverside@halcyon.health` | Field technician (Riverside Clinic) |
| `tech.pacific@halcyon.health` | Field technician (Pacific Medical) |
| `tech.desert@halcyon.health` | Field technician (Desert Outpatient) |

Login:

```bash
curl -s http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@halcyon.health","password":"Medflow123!"}'
```

Send the token as `Authorization: Bearer <access_token>`.

## API

All business routes live under `/api/v1`. List responses use `{ items, total, page, page_size }`.

| Method | Path | Admin | Technician | Auditor |
| --- | --- | --- | --- | --- |
| POST | `/auth/login` | public | public | public |
| GET | `/auth/me` | yes | yes | yes |
| CRUD | `/users` | full | self GET only | read |
| CRUD | `/hospitals` | full | read | read |
| CRUD | `/equipment` | full | read (own facility + assigned orders) | read |
| CRUD | `/work-orders` | full | own orders; status updates and report uploads | read |
| POST | `/work-orders/{id}/reports` | yes | assigned order only | no |
| GET | `/analytics/*` | yes | yes | yes |

### Analytics

- `GET /api/v1/analytics/low-charge` — available or in-use devices below 20% charge
- `GET /api/v1/analytics/colocation-discrepancies` — distinct devices on active work orders whose technician is at a different hospital
- `GET /api/v1/analytics/reliability` — completed/failed counts and completion rate by device model
- `GET /api/v1/analytics/maintenance-flags` — hospitals with more than 30% of devices in maintenance
- `GET /api/v1/analytics/reporting-lines?supervisor_id=` — technicians reporting to a supervisor who currently have active work orders
- `GET /api/v1/analytics/summary` — all five payloads for a dashboard

Service report files are stored locally under `backend/uploads` when `STORAGE_BACKEND=local`, and served from `/uploads/...`. Set `STORAGE_BACKEND=s3` plus `S3_BUCKET` to upload reports with `boto3` and return short-lived presigned URLs. Uploads are capped at 5 MB.

## AWS

`bin/deploy-aws.sh` builds the API on this machine, then creates a private single-AZ `db.t4g.micro` RDS instance, an ARM Lambda Function URL, a private reports bucket, and a CloudFront site in front of a private frontend bucket. While RDS is running that is about $0.50 per day. Secrets land in gitignored `backend/.env.aws`.

```bash
./bin/deploy-aws.sh
./bin/teardown-aws.sh
```

Demo accounts on the public site use the same password as local. Run teardown when the showcase is over. Stopping RDS only pauses the instance charge; deleting the stack is what ends it.

## Tests

```bash
source backend/.venv/bin/activate
cd backend
pytest
```

## Project layout

```text
bin/setup.sh
bin/seed.sh
docker-compose.yml
backend/app/          # FastAPI app, models, schemas, routers, analytics
backend/alembic/      # SQLAlchemy 2 / Postgres migrations
frontend/             # Vite + React + MUI command center
```
