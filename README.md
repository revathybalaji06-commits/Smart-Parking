# Smart Parking App

Real-time capacity tracking with a **dimensional matching algorithm** for size-aware parking slot reservation.

A first-semester systems project by A. Kamalesh, Kailesh, Thomas and Sachin.

## The problem

Most parking systems only report a single number: how many spaces are open. That hides the real cause of congestion, which is size mismatch rather than scarcity.

- Drivers still circle the aisles looking for a spot, wasting time and fuel.
- Every space counts the same, so a compact spot and a full-size spot are both "available".
- Oversized cars in undersized spots straddle lines and block neighbouring stalls.
- One blocked stall can back up the whole drive lane behind it.

Two lots that both show "12 spaces open" can differ greatly in how many of those spaces a given driver can actually use.

## The solution

The lot is modelled as a live inventory of individual, size-tagged slots instead of one shared pool. Three mechanics work together.

### 1. Real-time tracking

Counts update on every arrival and departure, overall and per size class:

```
Available = Max - Occupied
```

For example, a 50-space lot with 32 cars parked has 18 open spaces. Only the slots rated for the arriving vehicle's size class are offered as matches.

### 2. Dimensional matching (the core idea)

Before searching, the driver says what class of vehicle they are parking.

| Class | Name      | Fits                                    |
|-------|-----------|-----------------------------------------|
| 1     | Compact   | Compact cars and hatchbacks             |
| 2     | Sedan     | Mid-size sedans and coupes              |
| 3     | SUV       | SUVs and minivans                       |
| 4     | Full-Size | Full-size sedans and luxury cars        |

- The search is limited to slots rated for that class **or larger**.
- Among valid slots, the **smallest sufficient** one is reserved. A sedan is not given a full-size bay, which keeps large slots free for the cars that need them.
- The match is checked before a reservation is made, so a driver is never routed to a space their car cannot fit.

### 3. Dynamic routing

Each reservation is tied to one slot ID, not a general zone. Once the size match succeeds, the driver is guided directly to that specific space.

## Decision flow

```
Vehicle arrives
   └─ Is the lot full? ── yes ──> Reject entry (lot-full message)
         │ no
         v
   Identify vehicle size (Compact / Sedan / SUV / Full-Size)
         v
   Search the slot array for a fit
         v
   Match found? ── no ──> Reject, or offer the next size up
         │ yes
         v
   Mark slot occupied/reserved -> recalculate available count -> issue ticket and route driver
```

## Architecture

The target design has four layers:

| Layer     | Role                                                                                          | Planned tech                 |
|-----------|-----------------------------------------------------------------------------------------------|------------------------------|
| Frontend  | Driver enters vehicle class, gets a slot ID and route, sees live per-class availability       | React / React Native         |
| Backend   | API hosting the matching engine and capacity equation                                         | Node.js or Python (REST/GraphQL) |
| Database  | Durable slot and reservation state; the single source of truth                                | PostgreSQL (or Firebase)     |
| Sensing   | IoT sensors or beacons reporting arrivals and departures in real time                         | Simulated by keyboard input in the MVP |

The frontend never talks to the database directly. Every request goes through the backend API, which is the only owner of the matching logic. Sensor events and driver requests use the same API, so one decision flow governs both.

## Data model

Defined in [`schema.sql`](schema.sql) (PostgreSQL).

**`slots`**: one row per physical parking space

| Column       | Type        | Notes                                           |
|--------------|-------------|-------------------------------------------------|
| `id`         | serial PK   |                                                 |
| `lot_id`     | int         | Defaults to 1, so multiple lots can share a DB  |
| `label`      | text        | e.g. `C1`, `S12`, `U3`, `F8`                    |
| `size_class` | smallint    | 1-4 (Compact, Sedan, SUV, Full-Size)            |
| `status`     | text        | `free`, `occupied` or `reserved`                |
| `updated_at` | timestamptz |                                                 |

**`reservations`**: one row per reservation

| Column          | Type        | Notes                                                    |
|-----------------|-------------|----------------------------------------------------------|
| `id`            | serial PK   |                                                          |
| `slot_id`       | int FK      | References `slots(id)`                                   |
| `plate`         | text        | Vehicle plate                                            |
| `vehicle_class` | smallint    | 1-4                                                      |
| `status`        | text        | `active`, `completed`, `expired` or `cancelled`          |
| `created_at`    | timestamptz |                                                          |
| `expires_at`    | timestamptz | Optional                                                 |
| `ended_at`      | timestamptz | Optional                                                 |

### Seed data

[`seed.sql`](seed.sql) creates a 50-slot lot:

| Class     | Labels   | Count |
|-----------|----------|-------|
| Compact   | `C1-C10` | 10    |
| Sedan     | `S1-S20` | 20    |
| SUV       | `U1-U12` | 12    |
| Full-Size | `F1-F8`  | 8     |

## Getting started

Requires PostgreSQL.

```bash
createdb smart_parking
psql smart_parking -f schema.sql
psql smart_parking -f seed.sql
```

Example query: the best slot for a Sedan (class 2), meaning the smallest free slot that fits:

```sql
SELECT id, label, size_class
FROM slots
WHERE status = 'free' AND size_class >= 2
ORDER BY size_class, id
LIMIT 1;
```

Live availability per size class:

```sql
SELECT size_class,
       COUNT(*) FILTER (WHERE status = 'free') AS available,
       COUNT(*)                                AS max
FROM slots
GROUP BY size_class
ORDER BY size_class;
```

## Project status and roadmap

Currently in this repository: the database schema and seed data (week 1).

| Week | Phase               | Goals                                                                              |
|------|---------------------|------------------------------------------------------------------------------------|
| 1    | Database & core logic | Schema for slots, vehicles and reservations; dimensional matching search; live capacity equation |
| 2    | Backend API         | REST endpoints for reserve, arrive and depart; connect the engine to the DB; handle "no valid slot" and lot-full cases |
| 3    | Frontend & sensors  | Mobile/web driver interface; occupancy sensors or beacons; live routing to the assigned slot |
| 4    | Integration & launch | End-to-end testing; deployment; demo rehearsal                                     |

## Background and related work

The design is informed by the smart-parking literature, which treats parking as a constrained-resource matching problem rather than a counting problem:

- Channamallu et al., *A Review of Smart Parking Systems* (2023)
- Li et al., *MADM-Based Smart Parking Guidance Algorithm*, PLOS ONE (2017)
- Jemmali et al., *Smart-Parking Management Algorithms in Smart City*, Scientific Reports (2022)
- Bessghaier et al., *Smart Parking Reservation via Distributed Multicriteria Approach* (2017)
- Bagula et al., *Optimal Sensor Placement Model for Smart Parking Networks*, Sensors (2015)
- Ke et al., *Edge AI for Parking Surveillance on IoT Devices*, IEEE T-ITS
- Sarker et al., *Smart Parking with Dynamic Pricing, Edge-Cloud Computing & LoRa*, Sensors (2020)
- Floris et al., *A Social IoT-Based Platform for Smart Parking*, Computer Networks (2022)

Most existing work focuses on sensing and reporting whether a space is open. This project targets the remaining gap: whether a free space actually fits the vehicle.

## Team

| Name        | Roll number     |
|-------------|-----------------|
| A. Kamalesh | CB.AI.U4QTS26023 |
| Kailesh     | CB.AI.U4QTS26022 |
| Thomas      | CB.AI.U4QTS26050 |
| Sachin      | CB.AI.U4QTS26051 |
