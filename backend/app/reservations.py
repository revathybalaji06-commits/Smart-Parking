"""All the parking rules. No web code here, only database work.

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
        self.code, self.message, self.status = code, message, status


def free_expired_holds(conn):
    """Free slots whose 15-minute hold ran out before the car arrived."""
    conn.execute(
        """
        WITH old AS (
            UPDATE reservations SET status = 'expired', ended_at = now()
            WHERE status = 'active' AND expires_at < now()
            RETURNING slot_id
        )
        UPDATE slots SET status = 'free' WHERE id IN (SELECT slot_id FROM old)
        """
    )


def reserve(conn, plate, vehicle_class):
    """The core idea: give the car the SMALLEST free slot that it fits in."""
    # "tn 37 ab-1234" and "TN37AB1234" are the same car, so store one form
    plate = plate.replace(" ", "").replace("-", "").upper()
    if not plate.isalnum() or len(plate) > 12:
        raise ParkingError("invalid_request", "Plate must be letters and digits, at most 12.", 400)
    if vehicle_class < 1 or vehicle_class > 4:
        raise ParkingError("invalid_request", "Vehicle class must be 1 to 4.", 400)

    with conn.transaction():  # everything below is saved together, or not at all
        free_expired_holds(conn)

        # One car, one slot. The lock makes two requests for the same plate
        # wait for each other, so both cannot pass this check.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (plate,))
        if conn.execute(
            "SELECT 1 FROM reservations WHERE status = 'active' AND plate = %s", (plate,)
        ).fetchone():
            raise ParkingError("already_reserved", "This vehicle already has a reservation.", 409)

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
            if conn.execute("SELECT 1 FROM slots WHERE status = 'free'").fetchone():
                raise ParkingError("no_valid_slot", "No free slot is big enough for this vehicle.", 409)
            raise ParkingError("lot_full", "The parking lot is full.", 409)

        conn.execute("UPDATE slots SET status = 'reserved' WHERE id = %s", (slot["id"],))
        reservation_id = conn.execute(
            """
            INSERT INTO reservations (slot_id, plate, vehicle_class, expires_at)
            VALUES (%s, %s, %s, now() + make_interval(mins => %s))
            RETURNING id
            """,
            (slot["id"], plate, vehicle_class, HOLD_MINUTES),
        ).fetchone()["id"]

    return get_reservation(conn, reservation_id)


def change_state(conn, reservation_id, slot_must_be, new_slot_status, new_status):
    """Shared by arrive, depart and cancel: check the state, then change it."""
    free_expired_holds(conn)
    with conn.transaction():
        r = conn.execute(
            """
            SELECT r.status, r.slot_id, s.status AS slot_status
            FROM reservations r JOIN slots s ON s.id = r.slot_id
            WHERE r.id = %s
            FOR UPDATE OF r, s
            """,
            (reservation_id,),
        ).fetchone()
        if r is None:
            raise ParkingError("not_found", "Reservation not found.", 404)
        if r["status"] != "active" or r["slot_status"] != slot_must_be:
            raise ParkingError("invalid_state", "This cannot be done now.", 409)

        conn.execute("UPDATE slots SET status = %s WHERE id = %s", (new_slot_status, r["slot_id"]))
        if new_status == "active":  # arrived: the 15-minute timer no longer applies
            conn.execute("UPDATE reservations SET expires_at = NULL WHERE id = %s", (reservation_id,))
        else:
            conn.execute(
                "UPDATE reservations SET status = %s, ended_at = now() WHERE id = %s",
                (new_status, reservation_id),
            )
    return get_reservation(conn, reservation_id)


def arrive(conn, reservation_id):
    return change_state(conn, reservation_id, "reserved", "occupied", "active")


def depart(conn, reservation_id):
    return change_state(conn, reservation_id, "occupied", "free", "completed")


def cancel(conn, reservation_id):
    return change_state(conn, reservation_id, "reserved", "free", "cancelled")


def get_reservation(conn, reservation_id):
    """A reservation together with its slot (label, status and map position)."""
    row = conn.execute(
        """
        SELECT r.id AS reservation_id, r.plate, r.vehicle_class, r.status, r.expires_at,
               r.slot_id, s.label, s.size_class, s.status AS slot_status,
               s.x, s.y, s.width, s.height, s.access_x, s.access_y
        FROM reservations r JOIN slots s ON s.id = r.slot_id
        WHERE r.id = %s
        """,
        (reservation_id,),
    ).fetchone()
    if row is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    return row


def get_availability(conn):
    """Free slots per size class and in total. Available = Max - Occupied."""
    free_expired_holds(conn)
    rows = conn.execute(
        """
        SELECT size_class, count(*) FILTER (WHERE status = 'free') AS free, count(*) AS max
        FROM slots GROUP BY size_class ORDER BY size_class
        """
    ).fetchall()
    return {
        "lot": {"free": sum(r["free"] for r in rows), "max": sum(r["max"] for r in rows)},
        "classes": [
            {"class": r["size_class"], "name": CLASS_NAMES[r["size_class"]], "free": r["free"], "max": r["max"]}
            for r in rows
        ],
    }


def list_slots(conn):
    """Every slot with its status and position, used to draw the map."""
    free_expired_holds(conn)
    return conn.execute(
        "SELECT id, label, size_class, status, x, y, width, height FROM slots ORDER BY id"
    ).fetchall()
