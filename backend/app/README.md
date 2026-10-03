# backend/app

The API code of the Smart Parking backend (FastAPI + PostgreSQL). **This folder is intentionally empty of code; the team writes it here.**

## What belongs here

| File (to be created) | Purpose |
|----------------------|---------|
| `main.py`            | Creates the FastAPI app, enables CORS for the React frontend, and defines the HTTP endpoints listed in [`docs/api.md`](../../docs/api.md). |
| `reservations.py`    | The business logic: reserve the smallest free slot that fits a vehicle, then arrive, depart, cancel, expire stale holds, and compute availability. Contains no HTTP code. |
| `db.py`              | Opens the PostgreSQL connection using the `DATABASE_URL` environment variable. |
| `__init__.py`        | Empty file that makes this folder a Python package. |

## Rules
- Endpoints, field names and error codes must match [`docs/api.md`](../../docs/api.md) exactly. Change the contract first, in a PR, if something needs to differ.
- Every operation that changes slots and reservations must run in a single database transaction.
- The database tables are defined in [`db/schema.sql`](../../db/schema.sql). Do not create tables from Python.

## Run (after the code exists)
From the `backend/` folder: `uvicorn app.main:app --reload`
