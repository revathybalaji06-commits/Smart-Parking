"""Pretend traffic: other cars arrive and leave on their own.

A real lot has sensors that tell us when cars come and go. We have no sensors,
so this stands in for them. Every few seconds one car arrives or leaves, which
keeps the lot about 40% full. It never touches a slot that belongs to a
reservation made through the app.
"""
import asyncio

from .db import get_conn

TARGET_FULL = 0.40

# Slots taken by cars that did not come through the app
OTHER_CARS = """status = 'occupied'
                AND id NOT IN (SELECT slot_id FROM reservations WHERE status = 'active')"""

# Pick a random slot. SKIP LOCKED: if the app is reserving it right now, pick another.
RANDOM_FREE_SLOT = "SELECT id FROM slots WHERE status = 'free' ORDER BY random() LIMIT 1 FOR UPDATE SKIP LOCKED"
RANDOM_OTHER_CAR = f"SELECT id FROM slots WHERE {OTHER_CARS} ORDER BY random() LIMIT 1 FOR UPDATE SKIP LOCKED"


def tick(conn):
    """One car arrives if the lot is emptier than the target, otherwise one leaves."""
    with conn.transaction():
        row = conn.execute(
            f"SELECT count(*) AS total, count(*) FILTER (WHERE {OTHER_CARS}) AS others FROM slots"
        ).fetchone()
        if row["others"] < row["total"] * TARGET_FULL:
            new_status, which = "occupied", RANDOM_FREE_SLOT
        else:
            new_status, which = "free", RANDOM_OTHER_CAR
        conn.execute(
            f"UPDATE slots SET status = '{new_status}', updated_at = now() WHERE id = ({which})"
        )


def start_with_cars(conn):
    """When the server starts, put the first cars in the lot."""
    for _ in range(25):
        tick(conn)


async def run_forever():
    """Runs in the background while the server is on."""
    while True:
        await asyncio.sleep(12)
        try:
            conn = get_conn()
            tick(conn)
            conn.close()
        except Exception as error:  # keep going whatever happens
            print("simulator error:", error)
