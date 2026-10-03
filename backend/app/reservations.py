"""Reservation logic: reserve, arrive, depart, cancel.

reserve() finds the slot, marks it reserved and inserts the reservation in
ONE transaction. See docs/api.md for request/response shapes and errors.
"""
HOLD_MINUTES = 15


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
    WHERE status = 'free' AND size_class >= %(vehicle_class)s
    ORDER BY size_class, id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
"""

RESERVE_SLOT_SQL = """
    UPDATE slots SET status = 'reserved', updated_at = now() WHERE id = %(slot_id)s
"""

INSERT_RESERVATION_SQL = """
    INSERT INTO reservations (slot_id, plate, vehicle_class, expires_at)
    VALUES (%(slot_id)s, %(plate)s, %(vehicle_class)s,
            now() + make_interval(mins => %(hold)s))
    RETURNING id, status, expires_at
"""


def reserve(conn, plate, vehicle_class):
    """Reserve the smallest free slot that fits `vehicle_class` (1-4).

    Returns the dict from docs/api.md (POST /reserve).
    Raises ReservationError: invalid_request (400), lot_full or no_valid_slot (409).
    """
    plate = (plate or "").strip()
    if not plate:
        raise ReservationError("invalid_request", "plate is required.", 400)
    if not isinstance(vehicle_class, int) or isinstance(vehicle_class, bool) \
            or not 1 <= vehicle_class <= 4:
        raise ReservationError("invalid_request", "vehicle_class must be 1-4.", 400)

    with conn.transaction():
        slot = conn.execute(FIND_SLOT_SQL, {"vehicle_class": vehicle_class}).fetchone()

        if slot is None:
            free = conn.execute(
                "SELECT count(*) AS n FROM slots WHERE status = 'free'"
            ).fetchone()["n"]
            if free == 0:
                raise ReservationError("lot_full", "No free slots in the lot.", 409)
            raise ReservationError(
                "no_valid_slot", "No free slot fits this vehicle class.", 409
            )

        conn.execute(RESERVE_SLOT_SQL, {"slot_id": slot["id"]})
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
