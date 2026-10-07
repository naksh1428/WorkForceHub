# Employee Management API

A simple web API to keep track of employees and the departments they work in.

It is built with **FastAPI**, stores data in **MySQL**, and uses **Redis** to make repeat requests faster. You need to log in to use it.

## What it can do

- **Sign up and log in.** You get a token after logging in. Send this token with every other request.
- **Manage employees.** Add, view, change and remove employees.
- **Manage departments.** Add, list and remove departments. The list shows how many employees each department has.
- **Page through and search.** Get employees one page at a time, only from one department, or search by name or email.
- **Faster repeat requests.** Results are saved in Redis for a short time. When something changes, the saved results are cleared so you never see old data. If Redis is not running, the app still works, just a bit slower.
- **Clear errors.** Bad input or missing items give back clear error messages and the right status code.
- **Built-in docs.** Open `/docs` in your browser to see and try every route.

## How the code is organised

```
app/
├── main.py            # Starts the app and creates the database tables
├── core/
│   ├── config.py      # Reads settings from environment variables
│   └── security.py    # Password scrambling and login tokens
├── db/
│   ├── database.py    # Connects to the database
│   └── cache.py       # Saves and clears data in Redis
├── models/models.py   # Database tables: User, Department, Employee
├── schemas/schemas.py # Shapes of the data going in and out
└── api/
    ├── deps.py        # Finds the logged-in user from the token
    ├── auth.py        # /auth/register and /auth/login
    ├── employees.py   # /employees routes
    └── departments.py # /departments routes
```

**How saving in Redis works:** when you read data, the app first looks in Redis. If it finds it there, it sends it straight back. If not, it reads from the database and saves a copy in Redis. Any add, change or delete clears the related saved copies.

## Getting started

### Option 1: Docker (easiest)

This starts the API, MySQL and Redis together.

```bash
docker compose up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

The API waits until MySQL is ready before it starts.

### Option 2: Run it on your own machine

1. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy the example settings and change them to match your setup:

   ```bash
   cp .env.example .env
   ```

3. Make sure MySQL is running and the database exists:

   ```sql
   CREATE DATABASE employee_db;
   ```

   Want to skip MySQL? Use SQLite instead by setting this in `.env`:
   `DATABASE_URL=sqlite:///./employees.db`

4. Start the app:

   ```bash
   uvicorn app.main:app --reload
   ```

## Try it out

```bash
# 1. Sign up (you get a token back)
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "supersecret1"}'

# 2. Add a department
curl -X POST localhost:8000/departments \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Engineering"}'

# 3. Add an employee
curl -X POST localhost:8000/employees \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"first_name":"Jane","last_name":"Doe","email":"jane@example.com","job_title":"Python Developer","salary":55000,"hire_date":"2024-01-15","department_id":1}'

# 4. Search employees, 10 per page
curl "localhost:8000/employees?search=doe&page=1&page_size=10" \
  -H "Authorization: Bearer <TOKEN>"
```

Replace `<TOKEN>` with the token you got in step 1.

## All routes

| Method | Path              | What it does                                 | Login needed |
|--------|-------------------|----------------------------------------------|--------------|
| POST   | /auth/register    | Create an account and get a token            | No           |
| POST   | /auth/login       | Log in and get a token                       | No           |
| GET    | /employees        | List employees (pages, filter, search)       | Yes          |
| POST   | /employees        | Add an employee                              | Yes          |
| GET    | /employees/{id}   | Show one employee                            | Yes          |
| PATCH  | /employees/{id}   | Change some details of an employee           | Yes          |
| DELETE | /employees/{id}   | Remove an employee                           | Yes          |
| GET    | /departments      | List departments with employee counts        | Yes          |
| POST   | /departments      | Add a department                             | Yes          |
| DELETE | /departments/{id} | Remove a department and all its employees    | Yes          |
| GET    | /health           | Check if the app and Redis are running       | No           |

## Settings

Set these as environment variables or in a `.env` file (see `.env.example`).

| Name                        | Required | Default | What it is for                              |
|-----------------------------|----------|---------|---------------------------------------------|
| DATABASE_URL                | Yes      | –       | Where the database is                       |
| REDIS_URL                   | Yes      | –       | Where Redis is                              |
| JWT_SECRET_KEY              | Yes      | –       | Secret used to sign login tokens            |
| JWT_ALGORITHM               | No       | HS256   | How login tokens are signed                 |
| ACCESS_TOKEN_EXPIRE_MINUTES | No       | 30      | How long a login token works                |
| CACHE_TTL_SECONDS           | No       | 300     | How long results stay saved in Redis        |

Always use your own strong `JWT_SECRET_KEY` in production.

## Built with

Python 3.11+ · FastAPI · MySQL 8 · SQLAlchemy 2.0 · Pydantic v2 · Redis · PyJWT · passlib · Docker
