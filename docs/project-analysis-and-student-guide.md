# Smart Parking: Project Analysis and Student Guide

This guide explains the project in beginner-friendly language, maps its code to the presentation, and identifies which parts can be simplified safely. It describes the current code as inspected; it does not claim that planned hardware or multi-lot behavior is already implemented.

## 1. The project in one paragraph

A driver chooses a vehicle size (class 1–4) and submits a number plate. The React website sends that request to a Python/FastAPI server. The server asks PostgreSQL for the smallest free slot whose class is large enough, marks it reserved, and creates a reservation that expires after 15 minutes. The website then requests a route through a one-way-road graph and displays the route on an SVG map. Counts and slot states are refreshed from the server every five seconds. Other cars are simulated in the backend; physical sensors are not connected in this version.

## 2. The main idea: a size-aware match

The size classes are ordered from smallest to largest:

| Number | Class | Meaning in this demo |
|---:|---|---|
| 1 | Compact | Compact cars and hatchbacks |
| 2 | Sedan | Mid-size sedans and coupes |
| 3 | SUV | SUVs and minivans |
| 4 | Full-Size | Full-size and luxury cars |

The slot rule is:

```text
A slot fits if slot size >= vehicle size.
Choose the fitting free slot with the smallest size.
```

For example, a class-2 Sedan can use a class-2, class-3, or class-4 slot, but the search picks class 2 first if one is free. This leaves larger spaces for vehicles that need them. If all suitable slots are taken, the server rejects the request; it never assigns an undersized space.

The actual SQL that applies the rule is in `backend/app/reservations.py`, inside `reserve()`:

```sql
WHERE status = 'free' AND size_class >= requested_class
ORDER BY size_class, id
LIMIT 1
```

The important comparison is `>=`. The ordering makes the smallest adequate class come first. The database transaction and row lock around this search prevent two requests from taking the same slot at once.

## 3. What happens during a reservation

```text
Browser form
  -> POST /reserve
  -> FastAPI validates the JSON shape
  -> reserve() checks the plate and class
  -> expired holds are freed
  -> PostgreSQL finds and locks the smallest fitting slot
  -> slot changes free -> reserved
  -> reservation row is created with a 15-minute expiry
  -> browser remembers the reservation ID
  -> browser asks for the route and displays the assigned bay
```

A reservation then follows this lifecycle:

```text
reserve: free -> reserved
arrive:  reserved -> occupied
 depart: occupied -> free; reservation becomes completed
 cancel: reserved -> free; reservation becomes cancelled
 expire: reserved -> free; reservation becomes expired
```

`backend/app/reservations.py` owns these transitions. The website does not update the database directly; its buttons call API endpoints instead.

## 4. Where to read the code

### Backend: `backend/app/`

- `main.py` creates the FastAPI app, defines URLs, turns parking errors into JSON, and serves the built website if present.
- `reservations.py` contains the central parking rules: match a slot, reserve it, arrive, depart, cancel, expire holds, and count free spaces.
- `db.py` opens PostgreSQL connections and runs the schema and seed SQL at startup.
- `layout.py` defines the map junctions and one-way road edges, plus decorative map data.
- `routing.py` finds a path through the road graph and turns it into route points and readable directions.
- `simulator.py` periodically changes free slots to occupied and back to imitate other traffic. It avoids slots associated with active app reservations.

### Frontend: `frontend/src/`

- `main.jsx` starts React.
- `App.jsx` stores the page state, loads server data, submits actions, and joins the components together.
- `api.js` is the one place that makes HTTP requests.
- `ReserveForm.jsx` collects the plate and vehicle class.
- `Availability.jsx` displays total and per-class counts.
- `Reservation.jsx` displays the current reservation, directions, and arrive/cancel/depart controls.
- `LotMap.jsx` draws the map as SVG, including bays, one-way roads, the active route, and the moving dot.
- `useGuidance.js` moves that dot along the returned route and tracks the current direction step.
- `App.css` styles the page.

### Database and tests

- `db/schema.sql` defines the `slots` and `reservations` tables, validation constraints, and indexes.
- `db/generate_seed.py` calculates the 50 demo bay positions and checks that bays do not overlap.
- `db/seed.sql` is generated demo data; edit the generator, not the generated SQL.
- `backend/tests/test_parking.py`, `test_api.py`, and `test_routing.py` cover the main backend behavior.
- `docs/api.md` is the intended request/response contract between the web page and server.

## 5. The API, simply

The frontend and backend communicate using JSON over HTTP. The most important URLs are:

| Request | What it does |
|---|---|
| `GET /availability` | Gets total and per-size free counts |
| `GET /slots` | Gets slot states and positions for the map |
| `GET /layout` | Gets the road graph and map decorations |
| `POST /reserve` | Finds and reserves a fitting slot |
| `GET /reservations/{id}` | Gets one reservation |
| `GET /reservations/{id}/route` | Builds the route for an active reservation |
| `POST /reservations/{id}/arrive` | Marks the reserved slot occupied |
| `POST /reservations/{id}/depart` | Marks the slot free and completes the reservation |
| `POST /reservations/{id}/cancel` | Cancels a reservation before arrival |

`backend/app/main.py` connects each URL to a function. `frontend/src/api.js` contains the matching browser calls.

## 6. Availability math

A slot is available only when its database status is `free`. Reserved spaces are not available to a second driver. Therefore the count shown by this app is:

```text
available = number of slots with status "free"
```

For the full lot, this is equivalent to:

```text
available = maximum - occupied - reserved
```

This is a useful correction to a simplified slide formula such as `Max - Occupied`: that formula needs to account for reserved spaces too. The backend does so by counting only `free` slots.

The class cards count spaces of exactly that class. A Sedan's usable count is not just the Sedan card; it can also use any larger class that is free. The matching query accounts for that.

## 7. How route guidance works

The map is stored as a small graph:

- `NODES` are named road junctions with `(x, y)` coordinates.
- `EDGES` are directed road segments. A pair `("J1", "R1")` means traffic can go from J1 to R1, not necessarily the other way.
- Each slot stores an access point on the road.

`routing.py` measures each road segment, searches for the shortest path from `ENTRY` to the road beside the selected slot, then adds the final segment into the bay. It combines straight segments and produces text such as “Turn right and drive … m.” The frontend interpolates a position along the route to animate the blue dot. The dot is a visual simulation, not GPS.

## 8. What the presentation promises versus what this MVP does

The central idea in the slides—size matching before assigning a slot—is implemented. The backend also supports reservations, capacity counts, a map, one-way route guidance, and simulated occupancy.

Important scope differences:

1. **Sensors are simulated.** The backend's `simulator.py` is pretend traffic. There is no physical sensor, beacon, or keyboard sensor-integration service in the repository.
2. **The current app is effectively one-lot.** The schema has a `lot_id` column and a uniqueness key, but reservation, availability, and slot-list queries do not accept a lot ID or filter by one. The code therefore treats all rows as a shared pool. The slide/README claim that multiple lots safely share this application is ahead of the current implementation.
3. **The flow is driver-request based.** The app checks whether an appropriate free slot exists and then reserves it. The separate sensor-driven gate-open/closed process shown in the slide is not implemented as a physical entrance-control system.
4. **Simulated traffic is optional.** It runs by default; setting `SIMULATE_TRAFFIC=0` disables both the starting cars and the background simulator.
5. **Offline support is limited.** The service worker can keep the website files available offline, but live counts, reservations, and routes still need the backend/network.

These are useful presentation caveats: describe multi-lot support and physical IoT sensors as future work, not completed features.

## 9. Which code is already simple, and which parts are advanced

Most of the app is already separated into small, named files. For a first-semester student, the easiest learning order is:

1. `ReserveForm.jsx` — how a form gathers input.
2. `frontend/src/api.js` — how the browser sends a request.
3. `main.py` — how a URL reaches a backend function.
4. `reservations.py` — the main matching rule and lifecycle.
5. `schema.sql` — how records are stored.
6. `routing.py` and `LotMap.jsx` — the optional graph/map feature.
7. `simulator.py` and `useGuidance.js` — background traffic and animation.

Some complexity is there for correctness, not style. Do **not** remove these safeguards just to reduce line count:

- The database transaction and `FOR UPDATE SKIP LOCKED` reservation lock stop simultaneous drivers from receiving the same space.
- The unique partial index in `schema.sql` is a second database-level guard against two active reservations for one slot.
- The status checks stop actions such as departing before arriving.
- The expiry check prevents a late arrival from claiming a slot after its hold expires.
- The tests protect the rule that a smaller slot is never given to a larger vehicle.

For learning, simplify by understanding and explaining a module at a time—not by deleting those safety rules. A safe “plain English” version of the core algorithm is:

```text
check plate and vehicle class
free any expired reservations
look at free slots that are at least as large as the vehicle
choose the smallest such slot
if none exists, report why
otherwise mark the slot reserved and create the reservation
```

The code does this in SQL so the selection and locking can happen safely even when requests overlap.

## 10. Verification performed

- Python source compilation: **passed** (`compileall`).
- Frontend production build: **passed** (`npm run build`).
- Backend tests: **2 database-free configuration tests passed; 22 database-backed tests were skipped**, because `TEST_DATABASE_URL` was not set and PostgreSQL was unavailable at `localhost:5432`. The database-backed behavior still needs to be tested on a machine with a disposable test database.
- The test fixture drops and recreates the `slots` and `reservations` tables. Never point `TEST_DATABASE_URL` at a database containing data you need.

To run backend tests safely, start PostgreSQL, create a separate empty database such as `smart_parking_test`, and run:


```bash
cd backend
TEST_DATABASE_URL=postgresql://localhost/smart_parking_test ../.venv/bin/pytest -q
```

The precise connection URL may differ on your computer. The test database will be wiped by the fixture.

## 11. Recommended next steps for making it easier to study

1. Start with the matching query and trace one Sedan request through the API.
2. Draw the reservation states (`free → reserved → occupied → free`) and match each arrow to its function.
3. Run the frontend build and backend tests with a disposable PostgreSQL database.
4. Treat multi-lot selection as future work unless the backend adds a lot selector and filters all lot queries consistently. The documented simulated-traffic switch is now implemented.
5. Only after understanding the existing behavior, make readability changes in small steps and rerun the tests after each one. Keep the API response shapes and reservation lifecycle unchanged.
