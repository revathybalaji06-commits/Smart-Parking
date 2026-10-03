"""FastAPI app: CORS setup and route registration. Contract: docs/api.md."""
import os

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import reservations as svc
from .db import get_conn

app = FastAPI(title="Smart Parking API")

origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def error_response(error, message, status):
    return JSONResponse(status_code=status, content={"error": error, "message": message})


@app.exception_handler(svc.ReservationError)
def reservation_error_handler(request: Request, exc: svc.ReservationError):
    return error_response(exc.error, exc.message, exc.status)


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError):
    # The contract uses 400 invalid_request, not FastAPI's default 422
    return error_response("invalid_request", "Missing or malformed field.", 400)


class ReserveRequest(BaseModel):
    plate: str
    vehicle_class: int


@app.get("/availability")
def availability(conn=Depends(get_db)):
    return svc.get_availability(conn)


@app.get("/slots")
def slots(conn=Depends(get_db)):
    return svc.list_slots(conn)


@app.post("/reserve", status_code=201)
def reserve(body: ReserveRequest, conn=Depends(get_db)):
    return svc.reserve(conn, body.plate, body.vehicle_class)


@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: int, conn=Depends(get_db)):
    return svc.get_reservation(conn, reservation_id)


@app.post("/reservations/{reservation_id}/arrive")
def arrive(reservation_id: int, conn=Depends(get_db)):
    return svc.arrive(conn, reservation_id)


@app.post("/reservations/{reservation_id}/depart")
def depart(reservation_id: int, conn=Depends(get_db)):
    return svc.depart(conn, reservation_id)


@app.post("/reservations/{reservation_id}/cancel")
def cancel(reservation_id: int, conn=Depends(get_db)):
    return svc.cancel(conn, reservation_id)
