# Backend

FastAPI service and matching engine. Owners: Kamalesh and Sachin.

Implements the contract in [`../docs/api.md`](../docs/api.md). Schema and seed data live in [`../db`](../db).

```
app/main.py          routes, CORS, error handling
app/reservations.py  reserve / arrive / depart / cancel / expire / availability
app/db.py            connection (reads DATABASE_URL)
tests/               pytest suite (needs TEST_DATABASE_URL, see tests/conftest.py)
```

Run: `uvicorn app.main:app --reload` from this folder, with `DATABASE_URL` set. Interactive docs are at `/docs`.
Set `CORS_ORIGINS` (comma-separated) to the frontend's address; the default allows `localhost:5173` and `localhost:3000`.
