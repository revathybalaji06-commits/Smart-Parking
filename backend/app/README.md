# backend/app

The API code of the Smart Parking backend (FastAPI + PostgreSQL).

| File               | What it does |
|--------------------|--------------|
| `main.py`          | The web API. Each function is one URL from [`docs/api.md`](../../docs/api.md). Also sets up CORS, the error format, and serves the built website. |
| `reservations.py`  | All the parking logic: `reserve` (smallest free slot that fits), `arrive`, `depart`, `cancel`, expiry of unclaimed holds, availability. No web code. |
| `db.py`            | Opens the PostgreSQL connection (`DATABASE_URL`) and runs `db/schema.sql` + `db/seed.sql` when the server starts. |

## How reserving works (the core idea)
1. Take only slots that are `free` and whose size class is **the car's class or bigger**.
2. Sort them smallest first and take the first one, so large slots stay free for large cars.
3. Mark it `reserved` and save the reservation, all in one database transaction.
4. `FOR UPDATE SKIP LOCKED` makes sure two cars arriving at the same moment never get the same slot.

## Run
From the `backend/` folder: `uvicorn app.main:app --reload`
