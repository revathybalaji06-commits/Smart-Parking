"""Reservation logic: reserve, arrive, depart, cancel, expire, availability.

Every write runs in ONE transaction. See docs/api.md for shapes and errors.

Lifecycle:  reserve -> (slot 'reserved', reservation 'active', expires_at set)
            arrive  -> slot 'occupied', expires_at cleared
            depart  -> slot 'free', reservation 'completed'
            cancel  -> (before arrive) slot 'free', reservation 'cancelled'
            expire  -> (never arrived, past expires_at) slot 'free', reservation 'expired'
"""
HOLD_MINUTES = 15
CLASS_NAMES = {1: "Compact", 2: "Sedan", 3: "SUV", 4: "Full-Size"}


class ReservationError(Exception):
    """An error that maps to the error format in docs/api.md."""

    def __init__(self, error, message, status):
        super().__init__(message)
        self.error = error
        self.message = message
        self.status = status


FIND_SLOT_SQL = """
    SELECT id, label, size_class
    FROM slots
    WHERE lot_id = %(lot_id)s AND status = 'free' AND size_class >= %(vehicle_class)s
    ORDER BY size_class, id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
"""

INSERT_RESERVATION_SQL = """
    INSERT INTO reservations (slot_id, plate, vehicle_class, expires_at)
    VALUES (%(slot_id)s, %(plate)s, %(vehicle_class)s,
            now() + make_interval(mins => %(hold)s))
    RETURNING id, status, expires_at
"""

# Free slots whose hold ran out. Occupied slots are untouched: arrive clears expires_at.
EXPIRE_SQL = """
    WITH expired AS (
        UPDATE reservations
        SET status = 'expired', ended_at = now()
        WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at < now()
        RETURNING slot_id
    )
    UPDATE slots SET status = 'free', updated_at = now()
    WHERE id IN (SELECT slot_id FROM expired) AND status = 'reserved'
"""


def expire_stale(conn):
    """Release slots whose reservation was never claimed. Returns how many."""
    return conn.execute(EXPIRE_SQL).rowcount


def reserve(conn, plate, vehicle_class, lot_id=1):
    """Reserve the smallest free slot that fits `vehicle_class` (1-4).

    Returns the dict from docs/api.md (POST /reserve).
    Raises ReservationError: invalid_request (400), lot_full or no_valid_slot (409).
    """
    plate = plate.strip() if isinstance(plate, str) else ""
    if not plate:
        raise ReservationError("invalid_request", "plate is required.", 400)
    if not isinstance(vehicle_class, int) or isinstance(vehicle_class, bool) \
            or not 1 <= vehicle_class <= 4:
        raise ReservationError("invalid_request", "vehicle_class must be 1-4.", 400)

    with conn.transaction():
        expire_stale(conn)  # so an abandoned hold never blocks a new driver
        slot = conn.execute(
            FIND_SLOT_SQL, {"lot_id": lot_id, "vehicle_class": vehicle_class}
        ).fetchone()

        if slot is None:
            free = conn.execute(
                "SELECT count(*) AS n FROM slots WHERE lot_id = %s AND status = 'free'",
                (lot_id,),
            ).fetchone()["n"]
            if free == 0:
                raise ReservationError("lot_full", "No free slots in the lot.", 409)
            raise ReservationError(
                "no_valid_slot", "No free slot fits this vehicle class.", 409
            )

        conn.execute(
            "UPDATE slots SET status = 'reserved', updated_at = now() WHERE id = %s",
            (slot["id"],),
        )
        res = conn.execute(
            INSERT_RESERVATION_SQL,
            {
                "slot_id": slot["id"],
                "plate": plate,
                "vehicle_class": vehicle_class,
                "hold": HOLD_MINUTES,
            },
        ).fetchone()

    return {
        "reservation_id": res["id"],
        "slot_id": slot["id"],
        "label": slot["label"],
        "size_class": slot["size_class"],
        "status": res["status"],
        "expires_at": res["expires_at"].isoformat(),
    }


def _lock_reservation(conn, reservation_id):
    """Fetch a reservation and its slot, locked for the rest of the transaction."""
    row = conn.execute(
        """
        SELECT r.id, r.slot_id, r.status, r.expires_at,
               s.status AS slot_status
        FROM reservations r JOIN slots s ON s.id = r.slot_id
        WHERE r.id = %s
        FOR UPDATE OF r, s
        """,
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ReservationError("not_found", "Reservation not found.", 404)
    return row


def _set_slot(conn, slot_id, status):
    conn.execute(
        "UPDATE slots SET status = %s, updated_at = now() WHERE id = %s",
        (status, slot_id),
    )


def arrive(conn, reservation_id):
    """Driver reached the slot: reserved -> occupied. Clears the hold timer."""
    with conn.transaction():
        res = _lock_reservation(conn, reservation_id)
        if res["status"] != "active" or res["slot_status"] != "reserved":
            raise ReservationError(
                "invalid_state", f"Cannot arrive: reservation is {res['status']}.", 409
            )
        if res["expires_at"] is not None and conn.execute(
            "SELECT %s < now() AS gone", (res["expires_at"],)
        ).fetchone()["gone"]:
            raise ReservationError("invalid_state", "Reservation has expired.", 409)
        conn.execute(
            "UPDATE reservations SET expires_at = NULL WHERE id = %s", (reservation_id,)
        )
        _set_slot(conn, res["slot_id"], "occupied")
    return {
        "reservation_id": reservation_id,
        "slot_id": res["slot_id"],
        "slot_status": "occupied",
    }


def depart(conn, reservation_id):
    """Vehicle leaves: occupied -> free, reservation completed."""
    with conn.transaction():
        res = _lock_reservation(conn, reservation_id)
        if res["status"] != "active" or res["slot_status"] != "occupied":
            raise ReservationError(
                "invalid_state", "Cannot depart: vehicle has not arrived.", 409
            )
        conn.execute(
            "UPDATE reservations SET status = 'completed', ended_at = now() WHERE id = %s",
            (reservation_id,),
        )
        _set_slot(conn, res["slot_id"], "free")
    return {
        "reservation_id": reservation_id,
        "slot_id": res["slot_id"],
        "slot_status": "free",
        "status": "completed",
    }


def cancel(conn, reservation_id):
    """Driver cancels before arriving: reserved -> free, reservation cancelled."""
    with conn.transaction():
        res = _lock_reservation(conn, reservation_id)
        if res["status"] != "active" or res["slot_status"] != "reserved":
            raise ReservationError(
                "invalid_state", f"Cannot cancel: reservation is {res['status']}.", 409
            )
        conn.execute(
            "UPDATE reservations SET status = 'cancelled', ended_at = now() WHERE id = %s",
            (reservation_id,),
        )
        _set_slot(conn, res["slot_id"], "free")
    return {"reservation_id": reservation_id, "status": "cancelled"}


def get_reservation(conn, reservation_id):
    row = conn.execute(
        """
        SELECT r.id, r.plate, r.vehicle_class, r.slot_id, s.label, r.status,
               r.created_at, r.expires_at, r.ended_at
        FROM reservations r JOIN slots s ON s.id = r.slot_id
        WHERE r.id = %s
        """,
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ReservationError("not_found", "Reservation not found.", 404)
    iso = lambda t: t.isoformat() if t else None  # noqa: E731
    return {
        "reservation_id": row["id"],
        "plate": row["plate"],
        "vehicle_class": row["vehicle_class"],
        "slot_id": row["slot_id"],
        "label": row["label"],
        "status": row["status"],
        "created_at": iso(row["created_at"]),
        "expires_at": iso(row["expires_at"]),
        "ended_at": iso(row["ended_at"]),
    }


def get_availability(conn, lot_id=1):
    """Free/max per size class and for the whole lot (GET /availability)."""
    expire_stale(conn)
    rows = conn.execute(
        """
        SELECT size_class,
               count(*) FILTER (WHERE status = 'free') AS free,
               count(*) AS max
        FROM slots WHERE lot_id = %s
        GROUP BY size_class ORDER BY size_class
        """,
        (lot_id,),
    ).fetchall()
    return {
        "lot": {"free": sum(r["free"] for r in rows), "max": sum(r["max"] for r in rows)},
        "classes": [
            {
                "class": r["size_class"],
                "name": CLASS_NAMES[r["size_class"]],
                "free": r["free"],
                "max": r["max"],
            }
            for r in rows
        ],
    }


def list_slots(conn, lot_id=1):
    """All slots, for the lot map (GET /slots)."""
    expire_stale(conn)
    return conn.execute(
        "SELECT id, label, size_class, status FROM slots WHERE lot_id = %s ORDER BY id",
        (lot_id,),
    ).fetchall()
