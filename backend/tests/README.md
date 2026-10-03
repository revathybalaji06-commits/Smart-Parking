# backend/tests

Automated tests (pytest) for the backend code in [`backend/app`](../app). **Intentionally empty until the code is written.**

## What belongs here

| File (to be created) | Purpose |
|----------------------|---------|
| `conftest.py`        | Shared test setup: connects to a scratch database and recreates the tables from `db/schema.sql` and `db/seed.sql` before each test. |
| `test_reserve.py`    | Tests for reserving: smallest fitting slot, automatic upgrade to a larger class, `lot_full`, `no_valid_slot`, invalid input, two simultaneous requests never getting the same slot. |
| `test_lifecycle.py`  | Tests for arrive, depart, cancel, expiry of unclaimed reservations, and availability counts. |
| `test_api.py`        | Tests of the HTTP endpoints: status codes and JSON shapes from `docs/api.md`. |

## Rules
- Tests use their own database, set with the `TEST_DATABASE_URL` environment variable. Never point it at a database with data you want to keep: the tables are dropped and recreated.
- Run from the `backend/` folder: `pytest`
