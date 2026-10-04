# MedFlow

Centralized clinical equipment command center for Halcyon Health Systems. This repository ships the FastAPI backend, local Docker PostgreSQL database, and a React (Vite) + Material UI command center. AWS deploy comes later.

## Local setup

Requires Python 3.10+, Docker Desktop (daemon running), and Node.js 20+.

```bash
chmod +x bin/setup.sh bin/seed.sh
./bin/setup.sh
./bin/seed.sh
```

`bin/setup.sh` creates `backend/.venv`, installs Python dependencies, copies `backend/.env.example` to `backend/.env` (and generates `JWT_SECRET` if the file is new), starts Postgres 16, and runs Alembic migrations.

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

List grids support server-side pagination, search, status/role filters, and column sorting (`sort_by` / `sort_dir` on the API).

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

Service report files are stored locally under `backend/uploads` (`STORAGE_BACKEND=local`) and served from `/uploads/...`. S3 is not enabled yet.

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
