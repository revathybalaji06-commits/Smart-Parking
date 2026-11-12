# Smart Parking: Student Guide

A short guide for reading and explaining the code. The whole project is about 1,000 lines, including the tests and the SQL.

## 1. The project in one paragraph

A driver picks a vehicle size (class 1 to 4) and types a number plate. The web page sends that to the backend. The backend finds the **smallest free slot that fits**, holds it for 15 minutes, and returns the slot plus a route from the entry gate. The page draws the lot, the route and a moving dot. The driver then presses "I have arrived" and later "I am leaving".

## 2. The main idea: a size-aware match

A normal parking app only counts free spaces. This one asks whether a free space **fits**:

```sql
SELECT id, label, size_class FROM slots
WHERE status = 'free' AND size_class >= 2      -- a Sedan fits class 2, 3 or 4
ORDER BY size_class, id                        -- smallest fitting slot first
LIMIT 1
FOR UPDATE SKIP LOCKED;                        -- two cars never get the same slot
```

Available = Max - Occupied, counted per size class and for the whole lot.

## 3. Read the code in this order

| # | File | Lines | What to learn |
|---|------|-------|---------------|
| 1 | `db/schema.sql` | 37 | The two tables: `slots` and `reservations`. |
| 2 | `db/seed.sql` | 57 | The 50 bays and where each one is on the map. |
| 3 | `backend/app/db.py` | 20 | How Python connects to PostgreSQL. |
| 4 | `backend/app/reservations.py` | 169 | The parking rules. Start with `reserve`, then `change_state`. |
| 5 | `backend/app/main.py` | 108 | One small function per URL. |
| 6 | `backend/app/routing.py` | 111 | The road map and the shortest route. |
| 7 | `backend/app/simulator.py` | 41 | Pretend traffic (stands in for sensors). |
| 8 | `frontend/index.html` | 280 | The whole website: style, page, and script. |
| 9 | `backend/tests/test_parking.py` | 141 | Each test is a small example of a rule. |

## 4. Life of a reservation

| Action | Slot before | Slot after | Reservation after |
|--------|-------------|------------|-------------------|
| reserve | free | reserved | active (15-minute timer) |
| arrive | reserved | occupied | active (timer cleared) |
| depart | occupied | free | completed |
| cancel | reserved | free | cancelled |
| (timer runs out) | reserved | free | expired |

`arrive`, `depart` and `cancel` all use one function, `change_state`, which checks the "before" column and then writes the "after" columns inside one transaction.

## 5. How the route is found

- `NODES` are road junctions with `(x, y)` positions. `EDGES` are one-way road pieces between them.
- `shortest_path` keeps the best known distance to every junction. It goes over all road pieces again and again, and whenever a piece gives a shorter way it remembers it. (This is the Bellman-Ford method.)
- The route is: the junctions on the shortest path, then the spot on the road in front of the bay, then the bay.
- Straight pieces in a row are joined into one "leg". Each leg becomes one sentence. Left or right comes from the sign of a cross product.

## 6. Questions you may be asked

- **Why a transaction?** Marking the slot and saving the reservation must both happen or neither. Otherwise a slot could be reserved with no reservation.
- **What stops two cars getting one slot?** `FOR UPDATE SKIP LOCKED` locks the chosen row; a second request skips it and takes the next slot. A unique index (one active reservation per slot) is a second safety net.
- **What if the driver never comes?** The hold expires after 15 minutes and the slot is freed (`free_expired_holds`).
- **Where are the sensors?** Simulated. `simulator.py` moves other cars in and out, and the driver's buttons stand in for gate sensors.
- **Is there a login?** No. It is a known limit of this version.
- **Is the map a real Amrita car park?** No. It is a model of a typical campus lot.
