# backend

The server side of Smart Parking: a FastAPI service that holds the size-matching algorithm and talks to PostgreSQL. **Owners: Kamalesh and Sachin.**

| Path                | What it is |
|---------------------|------------|
| [`app/`](app)       | The API code (empty; to be written). |
| [`tests/`](tests)   | Automated tests (empty; to be written). |
| `requirements.txt`  | Python packages the backend needs. Install with `pip install -r requirements.txt` inside a virtual environment. |
| `.env.example`      | Template for settings: `DATABASE_URL` (which database to use) and `CORS_ORIGINS` (which frontend addresses may call the API). Copy to `.env`, which is git-ignored. |

The backend must follow the contract in [`../docs/api.md`](../docs/api.md) and use the tables in [`../db/schema.sql`](../db/schema.sql).
