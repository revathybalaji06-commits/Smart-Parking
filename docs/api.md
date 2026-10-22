# API Contract (v0.3)

This is the source of truth between the backend team (Kamalesh, Sachin) and the frontend team (Thomas, Kailesh).
Change it only through a PR that both teams approve.

- Base URL: configurable (`VITE_API_URL` on the frontend). Local default: `http://localhost:8000`.
- Format: JSON over HTTP. Timestamps are ISO 8601 UTC.
- Vehicle / size classes: `1` Compact, `2` Sedan, `3` SUV, `4` Full-Size.
- Slot status: `free`, `reserved`, `occupied`.

## Errors

All errors use the same shape:

```json
{ "error": "no_valid_slot", "message": "No free slot fits this vehicle class." }
```

| HTTP | `error` | Meaning |
|------|---------|---------|
| 400 | `invalid_request` | Missing or malformed field (e.g. class not in 1-4) |
| 404 | `not_found` | Reservation or slot does not exist |
| 409 | `lot_full` | No free slot of any size |
| 409 | `no_valid_slot` | Free slots exist, but all are smaller than the vehicle |
| 409 | `invalid_state` | Action not allowed in the current state (e.g. departing a cancelled reservation) |

## GET /availability

Live counts, overall and per size class. `free` = `max - occupied - reserved`.

```json
{
  "lot": { "free": 18, "max": 50 },
  "classes": [
    { "class": 1, "name": "Compact",   "free": 4, "max": 10 },
    { "class": 2, "name": "Sedan",     "free": 8, "max": 20 },
    { "class": 3, "name": "SUV",       "free": 4, "max": 12 },
    { "class": 4, "name": "Full-Size", "free": 2, "max": 8 }
  ]
}
```

`free` per class counts only slots of that exact class. For a vehicle of class N, usable slots are classes N and above.

## GET /slots

All slots, for drawing the lot map.

```json
[
  { "id": 1, "label": "C1", "size_class": 1, "status": "free",
    "row_name": "Row 1", "x": 5.9, "y": 40.0, "width": 4.6, "height": 2.4 }
]
```

`x`, `y`, `width`, `height` give the bay's rectangle on the map (units are roughly metres, `y` grows downward).

## GET /layout

Everything needed to draw the lot: size, one-way roads, gates, trees and buildings.

```json
{
  "width": 90, "height": 92, "road_width": 7,
  "edges": [ { "from": "ENTRY", "to": "J2", "x1": 14, "y1": 86, "x2": 14, "y2": 60 } ],
  "gates": { "entry": { "x": 14, "y": 86 }, "exit": { "x": 76, "y": 86 } },
  "trees": [ { "x": 25, "y": 24, "r": 1.8 } ],
  "buildings": [ { "name": "Security", "x": 38, "y": 76, "w": 14, "h": 8 } ]
}
```

Each edge is a one-way road piece, driven from `(x1, y1)` to `(x2, y2)`. Cars drive on the left.

## POST /reserve

Reserves the smallest free slot that fits the vehicle (class N or larger). If the vehicle's own class is full, the next larger class is used automatically. The slot is held for 15 minutes; an unclaimed hold expires and the slot is freed.

Request:

```json
{ "plate": "TN37AB1234", "vehicle_class": 2 }
```

Response `201`:

```json
{
  "reservation_id": 42,
  "slot_id": 14,
  "label": "S4",
  "size_class": 2,
  "status": "active",
  "expires_at": "2026-10-02T10:30:00Z"
}
```

Errors: `400 invalid_request`, `409 lot_full`, `409 no_valid_slot`.

## GET /reservations/{id}/route

The exact route from the entry gate to the reserved bay, following the one-way roads. Only for an `active` reservation (`409 invalid_state` otherwise).

```json
{
  "slot": { "id": 14, "label": "S4", "row_name": "Row 2", "size_class": 2 },
  "points": [ { "x": 14, "y": 86 }, { "x": 14, "y": 12 }, { "x": 47.45, "y": 12 }, { "x": 47.45, "y": 18 } ],
  "distances": [ 0, 74, 107.45, 113.45 ],
  "length_m": 113,
  "steps": [
    { "text": "Enter through the entry gate and drive straight for 74 m.", "point_index": 1, "distance": 74 }
  ]
}
```

`points` is the line to draw. `distances[i]` is how far along the route point `i` is, so a moving dot can be placed anywhere on it. Each step ends at `points[point_index]`, `distance` metres from the gate.

## POST /reservations/{id}/arrive

Vehicle has reached its slot; the slot becomes `occupied` and the hold timer is cleared.

Response `200`:

```json
{ "reservation_id": 42, "slot_id": 14, "slot_status": "occupied" }
```

Errors: `404 not_found`, `409 invalid_state` (e.g. reservation expired).

## POST /reservations/{id}/depart

Vehicle leaves; the reservation is `completed` and the slot becomes `free`.

Response `200`:

```json
{ "reservation_id": 42, "slot_id": 14, "slot_status": "free", "status": "completed" }
```

Errors: `404 not_found`, `409 invalid_state`.

## POST /reservations/{id}/cancel

Driver cancels before arriving; the slot becomes `free`.

Response `200`:

```json
{ "reservation_id": 42, "status": "cancelled" }
```

## GET /reservations/{id}

```json
{
  "reservation_id": 42,
  "plate": "TN37AB1234",
  "vehicle_class": 2,
  "slot_id": 14,
  "label": "S4",
  "status": "active",
  "created_at": "2026-10-02T10:15:00Z",
  "expires_at": "2026-10-02T10:30:00Z",
  "ended_at": null
}
```

Reservation `status`: `active`, `completed`, `expired`, `cancelled`.

## Decisions

- Larger slots are assigned **automatically** when the vehicle's own class is full (no `suggested_upgrade_class`).
- Reservation hold time: **15 minutes** (`HOLD_MINUTES` in `backend/app/reservations.py`).
- Authentication: none in the MVP.
- Validation errors return `400 invalid_request` (not FastAPI's default 422).
- Other cars: the server simulates cars arriving and leaving (stands in for entrance sensors) and keeps the lot about 40% full. It never changes a slot belonging to an app reservation. Set `SIMULATE_TRAFFIC=0` to turn it off.
- Live interactive docs when the backend runs: `/docs`.
