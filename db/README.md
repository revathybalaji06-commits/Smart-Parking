# Database

PostgreSQL schema and seed data. Owners: Kamalesh and Sachin.

```bash
createdb smart_parking
psql smart_parking -f db/schema.sql
psql smart_parking -f db/seed.sql
```

Both files are safe to run more than once. `seed.sql` creates the 50-slot lot (10 Compact, 20 Sedan, 12 SUV, 8 Full-Size); `(lot_id, label)` is unique so re-seeding never duplicates slots.
