# backend/tests

Automated tests (pytest) for the backend code in [`backend/app`](../app).

| File | What it does |
|------|--------------|
| `conftest.py` | Test setup: connects to a scratch database and recreates the tables and the 50 slots before each test. |
| `test_parking.py` | The tests: reserving (smallest fit, next size up, lot full, one slot per plate), arrive / depart / cancel / expiry, routes and directions, pretend traffic, and the API. |

Tests use their own database, set with `TEST_DATABASE_URL`. **Its tables are dropped and recreated**, so never point it at a database you want to keep.

```bash
createdb smart_parking_test
cd backend
TEST_DATABASE_URL=postgresql://localhost/smart_parking_test pytest
```
