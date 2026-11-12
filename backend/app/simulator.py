"""Pretend traffic: other cars arrive and leave on their own.

A real lot has sensors that tell us when cars come and go. We have none, so this
stands in for them and keeps the lot about 40% full. It never touches a slot
that belongs to a reservation made through the app.
"""
import asyncio

from .db import get_conn

# Slots taken by cars that did not come through the app
OTHER_CARS = "status = 'occupied' AND id NOT IN (SELECT slot_id FROM reservations WHERE status = 'active')"


def tick(conn):
    """One car arrives if the lot is under 40% full, otherwise one leaves."""
    with conn.transaction():
        row = conn.execute(
            f"SELECT count(*) AS total, count(*) FILTER (WHERE {OTHER_CARS}) AS others FROM slots"
        ).fetchone()
        if row["others"] < row["total"] * 0.40:
            new_status, which = "occupied", "status = 'free'"
        else:
            new_status, which = "free", OTHER_CARS
        # Pick one such slot at random. SKIP LOCKED: not one the app is reserving right now.
        conn.execute(
            f"""UPDATE slots SET status = '{new_status}' WHERE id =
                (SELECT id FROM slots WHERE {which} ORDER BY random() LIMIT 1 FOR UPDATE SKIP LOCKED)"""
        )


async def run_forever():
    """Runs in the background while the server is on: one car every 12 seconds."""
    while True:
        await asyncio.sleep(12)
        try:
            conn = get_conn()
            tick(conn)
            conn.close()
        except Exception as error:  # keep going whatever happens
            print("simulator error:", error)
