# db

The PostgreSQL database definition. **Owners: Kamalesh and Sachin.** This is the only place tables are defined.

| File         | What it does |
|--------------|--------------|
| `schema.sql` | Creates the `slots` table (one row per parking space, with size class 1-4 and status `free`/`reserved`/`occupied`), the `reservations` table (one row per reservation), and the indexes. Safe to run more than once. |
| `seed.sql`   | Fills `slots` with the demo lot of 50 spaces: 10 Compact (`C1-C10`), 20 Sedan (`S1-S20`), 12 SUV (`U1-U12`), 8 Full-Size (`F1-F8`). Safe to run more than once. |

## Set up a database
```bash
createdb smart_parking
psql smart_parking -f db/schema.sql
psql smart_parking -f db/seed.sql
```
Run these from the project root.
