"""All the parking logic. No web code in this file, only database work.

Life of a reservation:
    reserve -> slot is 'reserved' (held for 15 minutes)
    arrive  -> slot is 'occupied'
    depart  -> slot is 'free' again, reservation is 'completed'
    cancel  -> (before arriving) slot is 'free', reservation is 'cancelled'
    expire  -> (never arrived in time) slot is 'free', reservation is 'expired'
"""

HOLD_MINUTES = 15
CLASS_NAMES = {1: "Compact", 2: "Sedan", 3: "SUV", 4: "Full-Size"}


class ParkingError(Exception):
    """An error the driver should see, e.g. lot_full. status is the HTTP code."""

    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def free_expired_holds(conn):
    """Free slots whose 15-minute hold ran out before the car arrived."""
    conn.execute(
        """
        WITH old AS (
            UPDATE reservations SET status = 'expired', ended_at = now()
            WHERE status = 'active' AND expires_at < now()
            RETURNING slot_id
        )
        UPDATE slots SET status = 'free', updated_at = now()
        WHERE id IN (SELECT slot_id FROM old) AND status = 'reserved'
        """
    )


def set_slot(conn, slot_id, status):
    conn.execute(
        "UPDATE slots SET status = %s, updated_at = now() WHERE id = %s", (status, slot_id)
    )


def reserve(conn, plate, vehicle_class):
    """The core idea: give the car the SMALLEST free slot that it fits in."""
    plate = plate.strip()
    if plate == "":
        raise ParkingError("invalid_request", "Plate number is required.", 400)
    if vehicle_class < 1 or vehicle_class > 4:
        raise ParkingError("invalid_request", "Vehicle class must be 1 to 4.", 400)

    with conn.transaction():  # everything below is saved together, or not at all
        free_expired_holds(conn)

        # Slots of our class or bigger, smallest first.
        # FOR UPDATE SKIP LOCKED: if another car is taking a slot at this very
        # moment, skip it, so two cars can never get the same slot.
        slot = conn.execute(
            """
            SELECT id, label, size_class FROM slots
            WHERE status = 'free' AND size_class >= %s
            ORDER BY size_class, id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """,
            (vehicle_class,),
        ).fetchone()

        if slot is None:
            free_count = conn.execute(
                "SELECT count(*) AS n FROM slots WHERE status = 'free'"
            ).fetchone()["n"]
            if free_count == 0:
                raise ParkingError("lot_full", "The parking lot is full.", 409)
            raise ParkingError(
                "no_valid_slot", "No free slot is big enough for this vehicle.", 409
            )

        set_slot(conn, slot["id"], "reserved")
        reservation = conn.execute(
            """
            INSERT INTO reservations (slot_id, plate, vehicle_class, expires_at)
            VALUES (%s, %s, %s, now() + make_interval(mins => %s))
            RETURNING id, expires_at
            """,
            (slot["id"], plate, vehicle_class, HOLD_MINUTES),
        ).fetchone()

    return {
        "reservation_id": reservation["id"],
        "slot_id": slot["id"],
        "label": slot["label"],
        "size_class": slot["size_class"],
        "status": "active",
        "expires_at": reservation["expires_at"],
    }


def lock_reservation(conn, reservation_id, slot_must_be):
    """Find a reservation, lock it (and its slot) until we finish, and check its state."""
    row = conn.execute(
        """
        SELECT r.id, r.slot_id, r.status, r.expires_at < now() AS timed_out,
               s.status AS slot_status
        FROM reservations r JOIN slots s ON s.id = r.slot_id
        WHERE r.id = %s
        FOR UPDATE OF r, s
        """,
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    if row["status"] != "active" or row["slot_status"] != slot_must_be:
        raise ParkingError("invalid_state", "This cannot be done in the current state.", 409)
    return row


def arrive(conn, reservation_id):
    """The car reached its slot: reserved -> occupied."""
    with conn.transaction():
        r = lock_reservation(conn, reservation_id, slot_must_be="reserved")
        if r["timed_out"]:
            raise ParkingError("invalid_state", "The 15-minute hold has expired.", 409)
        # expires_at = NULL: once parked, the hold timer no longer applies
        conn.execute("UPDATE reservations SET expires_at = NULL WHERE id = %s", (reservation_id,))
        set_slot(conn, r["slot_id"], "occupied")
    return {"reservation_id": reservation_id, "slot_id": r["slot_id"], "slot_status": "occupied"}


def depart(conn, reservation_id):
    """The car leaves, so the slot is free for the next one: occupied -> free."""
    with conn.transaction():
        r = lock_reservation(conn, reservation_id, slot_must_be="occupied")
        conn.execute(
            "UPDATE reservations SET status = 'completed', ended_at = now() WHERE id = %s",
            (reservation_id,),
        )
        set_slot(conn, r["slot_id"], "free")
    return {"reservation_id": reservation_id, "slot_id": r["slot_id"],
            "slot_status": "free", "status": "completed"}


def cancel(conn, reservation_id):
    """The driver changes their mind before arriving: reserved -> free."""
    with conn.transaction():
        r = lock_reservation(conn, reservation_id, slot_must_be="reserved")
        conn.execute(
            "UPDATE reservations SET status = 'cancelled', ended_at = now() WHERE id = %s",
            (reservation_id,),
        )
        set_slot(conn, r["slot_id"], "free")
    return {"reservation_id": reservation_id, "status": "cancelled"}


def get_reservation(conn, reservation_id):
    row = conn.execute(
        """
        SELECT r.id AS reservation_id, r.plate, r.vehicle_class, r.slot_id, s.label,
               r.status, r.created_at, r.expires_at, r.ended_at
        FROM reservations r JOIN slots s ON s.id = r.slot_id
        WHERE r.id = %s
        """,
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    return row


def get_slot_for_route(conn, reservation_id):
    """The slot of an active reservation, with its position on the map."""
    row = conn.execute(
        """
        SELECT s.label, s.x, s.y, s.width, s.height, s.access_x, s.access_y, r.status
        FROM reservations r JOIN slots s ON s.id = r.slot_id
        WHERE r.id = %s
        """,
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    if row["status"] != "active":
        raise ParkingError("invalid_state", "This reservation is not active.", 409)
    return row


def get_availability(conn):
    """How many slots are free, per size class and in total.

    Available = Max - Occupied  (reserved slots also count as taken)
    """
    free_expired_holds(conn)
    rows = conn.execute(
        """
        SELECT size_class,
               count(*) FILTER (WHERE status = 'free') AS free,
               count(*) AS max
        FROM slots GROUP BY size_class ORDER BY size_class
        """
    ).fetchall()
    return {
        "lot": {"free": sum(r["free"] for r in rows), "max": sum(r["max"] for r in rows)},
        "classes": [
            {"class": r["size_class"], "name": CLASS_NAMES[r["size_class"]],
             "free": r["free"], "max": r["max"]}
            for r in rows
        ],
    }


def list_slots(conn):
    """Every slot with its status and position, used to draw the map of the lot."""
    free_expired_holds(conn)
    return conn.execute(
        "SELECT id, label, size_class, status, x, y, width, height FROM slots ORDER BY id"
    ).fetchall()
