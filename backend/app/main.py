"""The web API. Each function below is one URL from docs/api.md."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import reservations as parking
from .db import get_conn, setup_database


@asynccontextmanager
async def lifespan(app):
    # Runs once when the server starts: make sure the tables and slots exist
    conn = get_conn()
    setup_database(conn)
    conn.close()
    yield


app = FastAPI(title="Smart Parking API", lifespan=lifespan)

# CORS: lets the React app (on another address while developing) call this API
origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """Give each request its own database connection, closed afterwards."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


# ---- errors: always answer in the format {"error": ..., "message": ...} ----
@app.exception_handler(parking.ParkingError)
def handle_parking_error(request, error):
    return JSONResponse(
        status_code=error.status,
        content={"error": error.code, "message": error.message},
    )


@app.exception_handler(RequestValidationError)
def handle_bad_request(request, error):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_request", "message": "Missing or wrong field."},
    )


# ---- what the driver sends when reserving ----
class ReserveRequest(BaseModel):
    plate: str
    vehicle_class: int


# ---- the endpoints ----
@app.get("/availability")
def availability(conn=Depends(get_db)):
    return parking.get_availability(conn)


@app.get("/slots")
def slots(conn=Depends(get_db)):
    return parking.list_slots(conn)


@app.post("/reserve", status_code=201)
def reserve(body: ReserveRequest, conn=Depends(get_db)):
    return parking.reserve(conn, body.plate, body.vehicle_class)


@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int, conn=Depends(get_db)):
    return parking.get_reservation(conn, reservation_id)


@app.post("/reservations/{reservation_id}/arrive")
def arrive(reservation_id: int, conn=Depends(get_db)):
    return parking.arrive(conn, reservation_id)


@app.post("/reservations/{reservation_id}/depart")
def depart(reservation_id: int, conn=Depends(get_db)):
    return parking.depart(conn, reservation_id)


@app.post("/reservations/{reservation_id}/cancel")
def cancel(reservation_id: int, conn=Depends(get_db)):
    return parking.cancel(conn, reservation_id)


# ---- the website: once the frontend is built, serve it from the same server ----
# This must stay LAST, so the API URLs above are matched first.
website = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if website.exists():
    app.mount("/", StaticFiles(directory=website, html=True), name="website")
