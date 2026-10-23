"""Simulate other drivers because this project has no physical sensors yet."""

import asyncio
import os

from .db import get_conn

TARGET_FULL = 0.40


def traffic_is_enabled():
    """Traffic is on by default; SIMULATE_TRAFFIC=0 turns it off."""
    return os.environ.get("SIMULATE_TRAFFIC", "1") != "0"


def tick(conn):
    """Move one non-app car in or out to keep the lot near 40% full."""
    with conn.transaction():
        counts = conn.execute(
            """
            SELECT count(*) AS total,
                   count(*) FILTER (
                       WHERE status = 'occupied'
                         AND id NOT IN (
                             SELECT slot_id FROM reservations WHERE status = 'active'
                         )
                   ) AS other_cars
            FROM slots
            """
        ).fetchone()

        if counts["other_cars"] < counts["total"] * TARGET_FULL:
            # A free slot is available, so simulate one car arriving.
            conn.execute(
                """
                UPDATE slots
                SET status = 'occupied', updated_at = now()
                WHERE id = (
                    SELECT id FROM slots
                    WHERE status = 'free'
                    ORDER BY random()
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                """
            )
        else:
            # Otherwise remove one car that did not reserve through the app.
            conn.execute(
                """
                UPDATE slots
                SET status = 'free', updated_at = now()
                WHERE id = (
                    SELECT id FROM slots
                    WHERE status = 'occupied'
                      AND id NOT IN (
                          SELECT slot_id FROM reservations WHERE status = 'active'
                      )
                    ORDER BY random()
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                """
            )


def start_with_cars(conn):
    """Add a few simulated cars when the server starts."""
    for _ in range(25):
        tick(conn)


async def run_forever():
    """Run one traffic update every 12 seconds until the server stops."""
    while True:
        await asyncio.sleep(12)
        conn = None
        try:
            conn = get_conn()
            tick(conn)
        except Exception as error:
            # A temporary simulator error should not stop the web server.
            print("simulator error:", error)
        finally:
            if conn is not None:
                conn.close()
