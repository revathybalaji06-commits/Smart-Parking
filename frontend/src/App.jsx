import { useEffect, useState } from "react";
import * as api from "./api";
import Availability from "./Availability";
import LotMap from "./LotMap";
import ReserveForm from "./ReserveForm";
import Reservation from "./Reservation";
import useGuidance from "./useGuidance";

export default function App() {
  const [availability, setAvailability] = useState(null);
  const [slots, setSlots] = useState([]);
  const [layout, setLayout] = useState(null);
  const [reservation, setReservation] = useState(null);
  const [route, setRoute] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [errorMessage, setErrorMessage] = useState("");

  // Download the current lot state and restore this browser's reservation.
  async function refreshPageData() {
    try {
      const currentAvailability = await api.getAvailability();
      setAvailability(currentAvailability);
      const currentSlots = await api.getSlots();
      setSlots(currentSlots);

      const savedReservationId = localStorage.getItem("reservationId");
      if (!savedReservationId) {
        setReservation(null);
        return;
      }

      // A missing or finished reservation should not block a new booking.
      const savedReservation = await api
        .getReservation(savedReservationId)
        .catch(() => null);
      setReservation(savedReservation);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  // Load data when the app opens, and refresh it every five seconds.
  useEffect(() => {
    refreshPageData();
    api.getLayout().then(setLayout).catch((error) => setErrorMessage(error.message));

    const refreshTimer = setInterval(refreshPageData, 5000);
    return () => clearInterval(refreshTimer);
  }, []);

  // Run a button action, display any error, and then reload server data.
  async function runAction(action) {
    setErrorMessage("");
    try {
      await action();
    } catch (error) {
      setErrorMessage(error.message);
    }
    refreshPageData();
  }

  async function reserveSlot(plate, vehicleClass) {
    await runAction(async () => {
      const newReservation = await api.reserve(plate, vehicleClass);
      localStorage.setItem("reservationId", newReservation.reservation_id);
    });
  }

  const activeReservation =
    reservation?.status === "active" ? reservation : null;
  const mySlot = activeReservation
    ? slots.find((slot) => slot.id === activeReservation.slot_id)
    : null;
  const driverIsOnTheWay = mySlot?.status === "reserved";
  const reservationId = activeReservation?.reservation_id ?? null;

  // Load a route whenever the active reservation changes.
  useEffect(() => {
    setRoute(null);
    if (reservationId) {
      api.getRoute(reservationId).then(setRoute).catch(() => {});
    }
  }, [reservationId]);

  const guidance = useGuidance(driverIsOnTheWay ? route : null);

  return (
    <main className="page">
      <h1>Smart Parking</h1>
      <p className="subtitle">
        Tell us your vehicle size and we reserve a slot that fits.
      </p>

      {errorMessage && <div className="error">{errorMessage}</div>}

      <h2>Available slots</h2>
      <Availability availability={availability} />

      {activeReservation ? (
        <Reservation
          reservation={activeReservation}
          slotStatus={mySlot?.status}
          guide={guidance}
          routeLength={route?.length_m}
          run={runAction}
          api={api}
        />
      ) : (
        <ReserveForm onReserve={reserveSlot} />
      )}

      <div className="map-head">
        <h2>Parking lot</h2>
        <div className="zoom">
          <button
            className="grey small"
            onClick={() => setZoom(Math.max(1, zoom - 0.5))}
          >
            -
          </button>
          Zoom
          <button
            className="grey small"
            onClick={() => setZoom(Math.min(3, zoom + 0.5))}
          >
            +
          </button>
        </div>
      </div>

      <LotMap
        layout={layout}
        slots={slots}
        mySlotId={activeReservation?.slot_id}
        route={driverIsOnTheWay ? route : null}
        dot={guidance.dot}
        zoom={zoom}
      />

      <div className="legend">
        <span className="swatch free" /> free
        <span className="swatch reserved" /> reserved
        <span className="swatch occupied" /> parked car
        <span className="swatch route" /> your route. Roads are one-way (arrows).
      </div>
    </main>
  );
}
