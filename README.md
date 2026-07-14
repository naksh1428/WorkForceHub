# Employee Management API

A production-style REST API for managing employees and departments, built with **FastAPI**, **MySQL** (SQLAlchemy 2.0) and **Redis caching**. JWT-secured, fully tested, linted, type-checked and shipped with CI/CD.

## Features

- **JWT authentication** — register/login, all business endpoints protected
- **Employee CRUD** — create, read, update (PATCH), delete
- **Departments** — with live employee counts
- **Pagination, filtering & search** — `?page=`, `?page_size=`, `?department_id=`, `?search=`
- **Redis caching** — GET responses cached with TTL, automatically invalidated on writes; graceful fallback if Redis is down (API keeps working)
- **Validation & error handling** — Pydantic v2 schemas, correct HTTP status codes (401/404/409/422)
- **MySQL persistence** — SQLAlchemy 2.0 ORM with connection pooling (`pool_pre_ping`, `pool_recycle`) and startup retry while MySQL boots
- **Quality standards** — typed code, ruff linting, pytest suite (21 tests), GitHub Actions CI
- **Auto-generated docs** — Swagger UI at `/docs`, OpenAPI at `/openapi.json`

## Architecture

```
app/
├── main.py            # FastAPI app, routers, lifespan (creates tables)
├── core/
│   ├── config.py      # Settings from env vars (pydantic-settings)
│   └── security.py    # Password hashing (passlib) + JWT (PyJWT)
├── db/
│   ├── database.py    # SQLAlchemy engine, session, Base
│   └── cache.py       # Redis wrapper: get/set/invalidate, fallback if down
├── models/models.py   # ORM models: User, Department, Employee
├── schemas/schemas.py # Pydantic request/response schemas
└── api/
    ├── deps.py        # get_current_user auth dependency
    ├── auth.py        # /auth/register, /auth/login
    ├── employees.py   # /employees CRUD + pagination + caching
    └── departments.py # /departments CRUD + caching
tests/                 # pytest suite (auth, CRUD, caching, validation)
```

**Caching strategy:** read endpoints check Redis first (`employees:id:{id}`, `employees:list:{...}`, `departments:all`). Any write (POST/PATCH/DELETE) invalidates the affected key patterns, so reads are always consistent.

## Quick start

### Option 1 — Docker (API + MySQL + Redis) — recommended

```bash
docker compose up --build
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
# MySQL 8.4 and Redis start automatically; the API waits for MySQL health.
```

### Option 2 — Local

```bash
pip install -r requirements-dev.txt
# Point at your own MySQL (create the database first):
#   CREATE DATABASE employee_db;
export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/employee_db"
uvicorn app.main:app --reload
# Tip: for a quick dependency-free run use SQLite instead:
#   export DATABASE_URL="sqlite:///./employees.db"
```

## Usage example

```bash
# 1. Register (returns a JWT)
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "supersecret1"}'

# 2. Create a department
curl -X POST localhost:8000/departments \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Engineering"}'

# 3. Create an employee
curl -X POST localhost:8000/employees \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"first_name":"Jane","last_name":"Doe","email":"jane@example.com","job_title":"Python Developer","salary":55000,"hire_date":"2024-01-15","department_id":1}'

# 4. Search with pagination
curl "localhost:8000/employees?search=doe&page=1&page_size=10" \
  -H "Authorization: Bearer <TOKEN>"
```

## Running tests & checks

```bash
pytest -v          # 21 tests; run against in-memory SQLite + fakeredis
                   # so CI needs no database server and stays fast
ruff check app tests
mypy app
```

CI runs all three automatically on every push and pull request (see `.github/workflows/ci.yml`).

## API reference

| Method | Path                 | Description                          | Auth |
|--------|----------------------|--------------------------------------|------|
| POST   | /auth/register       | Create user, returns JWT             | –    |
| POST   | /auth/login          | Login (OAuth2 form), returns JWT     | –    |
| GET    | /employees           | List (paginated, filter, search)     | ✔    |
| POST   | /employees           | Create employee                      | ✔    |
| GET    | /employees/{id}      | Get employee (cached)                | ✔    |
| PATCH  | /employees/{id}      | Partial update (invalidates cache)   | ✔    |
| DELETE | /employees/{id}      | Delete (invalidates cache)           | ✔    |
| GET    | /departments         | List with employee counts (cached)   | ✔    |
| POST   | /departments         | Create department                    | ✔    |
| DELETE | /departments/{id}    | Delete department + its employees    | ✔    |
| GET    | /health              | API + Redis status                   | –    |

## Configuration

All settings come from environment variables (see `.env.example`):

| Variable            | Default                      | Purpose                  |
|---------------------|------------------------------|--------------------------|
| DATABASE_URL        | mysql+pymysql://...:3306/employee_db | Any SQLAlchemy URL |
| REDIS_URL           | redis://localhost:6379/0     | Redis connection         |
| JWT_SECRET_KEY      | change-me-in-production      | Token signing key        |
| CACHE_TTL_SECONDS   | 300                          | Cache expiry             |

## Tech stack

Python 3.11+ · FastAPI · MySQL 8 (PyMySQL) · SQLAlchemy 2.0 · Pydantic v2 · Redis · PyJWT · passlib · pytest · fakeredis · ruff · mypy · GitHub Actions · Docker