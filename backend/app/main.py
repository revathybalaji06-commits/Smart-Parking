"""FastAPI application: startup, request handling, and website serving."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import reservations as parking
from . import routing, simulator
from .db import get_conn, setup_database
from .layout import LAYOUT


@asynccontextmanager
async def lifespan(app):
    """Prepare the database and run simulated traffic while the server is open."""
    conn = get_conn()
    try:
        setup_database(conn)
        if simulator.traffic_is_enabled():
            simulator.start_with_cars(conn)
    finally:
        conn.close()

    traffic_task = None
    if simulator.traffic_is_enabled():
        traffic_task = asyncio.create_task(simulator.run_forever())

    yield

    if traffic_task is not None:
        traffic_task.cancel()
        try:
            await traffic_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Smart Parking API", lifespan=lifespan)


# Give each web request its own database connection, then close it.
def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


@app.exception_handler(parking.ParkingError)
def handle_parking_error(request, error):
    """Return parking errors in the same JSON format for every endpoint."""
    return JSONResponse(
        status_code=error.status,
        content={"error": error.code, "message": error.message},
    )


@app.exception_handler(RequestValidationError)
def handle_bad_request(request, error):
    """Use the project's 400 error format for invalid request data."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "message": "Missing or wrong field.",
        },
    )


class ReserveRequest(BaseModel):
    """The JSON fields sent to POST /reserve."""

    plate: str
    vehicle_class: int


@app.get("/availability")
def availability(conn=Depends(get_db)):
    return parking.get_availability(conn)


@app.get("/slots")
def slots(conn=Depends(get_db)):
    return parking.list_slots(conn)


@app.get("/layout")
def layout():
    return LAYOUT


@app.post("/reserve", status_code=201)
def reserve(body: ReserveRequest, conn=Depends(get_db)):
    return parking.reserve(conn, body.plate, body.vehicle_class)


@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int, conn=Depends(get_db)):
    return parking.get_reservation(conn, reservation_id)


@app.get("/reservations/{reservation_id}/route")
def get_route(reservation_id: int, conn=Depends(get_db)):
    slot = parking.get_slot_for_route(conn, reservation_id)
    return routing.build_route(slot)


@app.post("/reservations/{reservation_id}/arrive")
def arrive(reservation_id: int, conn=Depends(get_db)):
    return parking.arrive(conn, reservation_id)


@app.post("/reservations/{reservation_id}/depart")
def depart(reservation_id: int, conn=Depends(get_db)):
    return parking.depart(conn, reservation_id)


@app.post("/reservations/{reservation_id}/cancel")
def cancel(reservation_id: int, conn=Depends(get_db)):
    return parking.cancel(conn, reservation_id)


# Keep this route last so the API routes above are handled first.
website_folder = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if website_folder.exists():
    app.mount("/", StaticFiles(directory=website_folder, html=True), name="website")
