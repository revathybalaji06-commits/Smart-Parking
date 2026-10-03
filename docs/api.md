# API Contract (v0.2)

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
  { "id": 1, "label": "C1", "size_class": 1, "status": "free" },
  { "id": 11, "label": "S1", "size_class": 2, "status": "occupied" }
]
```

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
- Live interactive docs when the backend runs: `/docs`.
