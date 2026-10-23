# Backend tests

These pytest tests check the parking rules, API responses, routes, simulated traffic, and traffic configuration.

## Test files

- `test_parking.py` checks slot matching, invalid input, reservation states, expiry, and availability.
- `test_api.py` checks endpoint responses and error codes.
- `test_routing.py` checks map routes, directions, and simulated cars.
- `test_simulator_config.py` checks whether the traffic simulator can be enabled or disabled.
- `conftest.py` prepares a fresh database for tests that need PostgreSQL.

## Run the tests safely

The database tests require a separate, disposable PostgreSQL database. The fixture drops and recreates the `slots` and `reservations` tables before each database test. **Never use a database that contains data you need.**

```bash
createdb smart_parking_test
cd backend
TEST_DATABASE_URL=postgresql://localhost/smart_parking_test pytest -q
```

Adjust the connection URL if PostgreSQL is configured differently on your computer. Tests that only check simulator configuration do not need a database.
