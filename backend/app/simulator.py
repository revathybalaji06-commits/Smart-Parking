"""Pretend traffic: other cars arrive and leave on their own.

A real lot has sensors that tell us when cars come and go. We do not have
sensors, so this stands in for them. Every few seconds one car arrives or
leaves, keeping the lot about 40% full. It never touches a slot that belongs to
a reservation made through the app.
"""
import asyncio
import random

from .db import get_conn

TARGET_FULL = 0.40
EVERY_SECONDS = 12

# slots taken by cars that did not come through the app
OTHER_CARS = """status = 'occupied'
                AND id NOT IN (SELECT slot_id FROM reservations WHERE status = 'active')"""


def tick(conn):
    """One car arrives or leaves. Returns 'arrived', 'left' or None."""
    with conn.transaction():
        row = conn.execute(
            f"SELECT count(*) AS total, count(*) FILTER (WHERE {OTHER_CARS}) AS others FROM slots"
        ).fetchone()
        wanted = row["total"] * TARGET_FULL

        # Below the target: more likely a car arrives. Above it: more likely one leaves.
        chance_arrive = 0.8 if row["others"] < wanted - 2 else 0.2 if row["others"] > wanted + 2 else 0.5
        if random.random() < chance_arrive:
            done = conn.execute(
                """UPDATE slots SET status = 'occupied', updated_at = now()
                   WHERE id = (SELECT id FROM slots WHERE status = 'free'
                               ORDER BY random() LIMIT 1 FOR UPDATE SKIP LOCKED)"""
            ).rowcount
            return "arrived" if done else None

        done = conn.execute(
            f"""UPDATE slots SET status = 'free', updated_at = now()
                WHERE id = (SELECT id FROM slots WHERE {OTHER_CARS}
                            ORDER BY random() LIMIT 1 FOR UPDATE SKIP LOCKED)"""
        ).rowcount
        return "left" if done else None


def warm_up(conn):
    """When the server starts, make sure the lot already has cars in it."""
    for _ in range(100):
        row = conn.execute(
            f"SELECT count(*) AS total, count(*) FILTER (WHERE {OTHER_CARS}) AS others FROM slots"
        ).fetchone()
        if row["others"] >= row["total"] * TARGET_FULL - 2:
            return
        tick(conn)


async def run_forever():
    """Runs in the background while the server is on."""
    while True:
        await asyncio.sleep(EVERY_SECONDS)
        try:
            conn = get_conn()
            await asyncio.to_thread(tick, conn)
            conn.close()
        except Exception as error:  # keep going whatever happens
            print("simulator error:", error)
