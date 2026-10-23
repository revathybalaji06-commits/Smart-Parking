"""Parking rules: choosing a slot and changing a reservation's state."""

HOLD_MINUTES = 15
CLASS_NAMES = {
    1: "Compact",
    2: "Sedan",
    3: "SUV",
    4: "Full-Size",
}


class ParkingError(Exception):
    """An error the API can safely show to the driver."""

    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def free_expired_holds(conn):
    """Free reservations that were not claimed within 15 minutes."""
    conn.execute(
        """
        WITH expired AS (
            UPDATE reservations
            SET status = 'expired', ended_at = now()
            WHERE status = 'active' AND expires_at < now()
            RETURNING slot_id
        )
        UPDATE slots
        SET status = 'free', updated_at = now()
        WHERE id IN (SELECT slot_id FROM expired)
          AND status = 'reserved'
        """
    )


def set_slot_status(conn, slot_id, status):
    """Save a slot's new state and the time it changed."""
    conn.execute(
        "UPDATE slots SET status = %s, updated_at = now() WHERE id = %s",
        (status, slot_id),
    )


def reserve(conn, plate, vehicle_class):
    """Reserve the smallest free slot that is large enough for the vehicle."""
    plate = plate.strip()
    if not plate:
        raise ParkingError("invalid_request", "Plate number is required.", 400)
    if vehicle_class < 1 or vehicle_class > 4:
        raise ParkingError("invalid_request", "Vehicle class must be 1 to 4.", 400)

    # Keep the slot selection and both database updates together. If any step
    # fails, PostgreSQL rolls the whole transaction back.
    with conn.transaction():
        free_expired_holds(conn)

        # >= means this slot fits the vehicle. Ordering by size picks the
        # smallest suitable slot. The row lock prevents double-booking.
        slot = conn.execute(
            """
            SELECT id, label, size_class
            FROM slots
            WHERE status = 'free' AND size_class >= %s
            ORDER BY size_class, id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """,
            (vehicle_class,),
        ).fetchone()

        if slot is None:
            free_slots = conn.execute(
                "SELECT count(*) AS count FROM slots WHERE status = 'free'"
            ).fetchone()["count"]
            if free_slots == 0:
                raise ParkingError("lot_full", "The parking lot is full.", 409)
            raise ParkingError(
                "no_valid_slot",
                "No free slot is big enough for this vehicle.",
                409,
            )

        set_slot_status(conn, slot["id"], "reserved")
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


def lock_reservation(conn, reservation_id, required_slot_status):
    """Load and lock a reservation and slot before changing their states."""
    reservation = conn.execute(
        """
        SELECT r.id, r.slot_id, r.status,
               r.expires_at < now() AS timed_out,
               s.status AS slot_status
        FROM reservations AS r
        JOIN slots AS s ON s.id = r.slot_id
        WHERE r.id = %s
        FOR UPDATE OF r, s
        """,
        (reservation_id,),
    ).fetchone()

    if reservation is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    if (reservation["status"] != "active"
            or reservation["slot_status"] != required_slot_status):
        raise ParkingError(
            "invalid_state", "This cannot be done in the current state.", 409
        )
    return reservation


def arrive(conn, reservation_id):
    """The driver has reached the bay: reserved becomes occupied."""
    with conn.transaction():
        reservation = lock_reservation(
            conn, reservation_id, required_slot_status="reserved"
        )
        if reservation["timed_out"]:
            raise ParkingError(
                "invalid_state", "The 15-minute hold has expired.", 409
            )

        # The timer only applies before arrival.
        conn.execute(
            "UPDATE reservations SET expires_at = NULL WHERE id = %s",
            (reservation_id,),
        )
        set_slot_status(conn, reservation["slot_id"], "occupied")

    return {
        "reservation_id": reservation_id,
        "slot_id": reservation["slot_id"],
        "slot_status": "occupied",
    }


def depart(conn, reservation_id):
    """The driver leaves: the slot becomes free and the reservation completes."""
    with conn.transaction():
        reservation = lock_reservation(
            conn, reservation_id, required_slot_status="occupied"
        )
        conn.execute(
            """
            UPDATE reservations
            SET status = 'completed', ended_at = now()
            WHERE id = %s
            """,
            (reservation_id,),
        )
        set_slot_status(conn, reservation["slot_id"], "free")

    return {
        "reservation_id": reservation_id,
        "slot_id": reservation["slot_id"],
        "slot_status": "free",
        "status": "completed",
    }


def cancel(conn, reservation_id):
    """Cancel a reservation before arrival and free its slot."""
    with conn.transaction():
        reservation = lock_reservation(
            conn, reservation_id, required_slot_status="reserved"
        )
        conn.execute(
            """
            UPDATE reservations
            SET status = 'cancelled', ended_at = now()
            WHERE id = %s
            """,
            (reservation_id,),
        )
        set_slot_status(conn, reservation["slot_id"], "free")

    return {"reservation_id": reservation_id, "status": "cancelled"}


def get_reservation(conn, reservation_id):
    """Return reservation details for the website."""
    reservation = conn.execute(
        """
        SELECT r.id AS reservation_id, r.plate, r.vehicle_class,
               r.slot_id, s.label, r.status, r.created_at,
               r.expires_at, r.ended_at
        FROM reservations AS r
        JOIN slots AS s ON s.id = r.slot_id
        WHERE r.id = %s
        """,
        (reservation_id,),
    ).fetchone()

    if reservation is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    return reservation


def get_slot_for_route(conn, reservation_id):
    """Get the map position of a slot for an active reservation."""
    slot = conn.execute(
        """
        SELECT s.label, s.x, s.y, s.width, s.height,
               s.access_x, s.access_y, r.status
        FROM reservations AS r
        JOIN slots AS s ON s.id = r.slot_id
        WHERE r.id = %s
        """,
        (reservation_id,),
    ).fetchone()

    if slot is None:
        raise ParkingError("not_found", "Reservation not found.", 404)
    if slot["status"] != "active":
        raise ParkingError(
            "invalid_state", "This reservation is not active.", 409
        )
    return slot


def get_availability(conn):
    """Count free slots for the whole lot and for each exact size class."""
    free_expired_holds(conn)
    rows = conn.execute(
        """
        SELECT size_class,
               count(*) FILTER (WHERE status = 'free') AS free,
               count(*) AS maximum
        FROM slots
        GROUP BY size_class
        ORDER BY size_class
        """
    ).fetchall()

    total_free = sum(row["free"] for row in rows)
    total_slots = sum(row["maximum"] for row in rows)
    classes = []
    for row in rows:
        classes.append({
            "class": row["size_class"],
            "name": CLASS_NAMES[row["size_class"]],
            "free": row["free"],
            "max": row["maximum"],
        })

    return {
        "lot": {"free": total_free, "max": total_slots},
        "classes": classes,
    }


def list_slots(conn):
    """Return slots and their map positions for drawing the lot."""
    free_expired_holds(conn)
    return conn.execute(
        """
        SELECT id, label, size_class, status, x, y, width, height
        FROM slots
        ORDER BY id
        """
    ).fetchall()
