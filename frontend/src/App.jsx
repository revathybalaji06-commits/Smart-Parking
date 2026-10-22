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
  const [layout, setLayout] = useState(null); // roads, gates, trees
  const [reservation, setReservation] = useState(null); // my reservation
  const [route, setRoute] = useState(null); // the way from the gate to my slot
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState("");

  // Reload everything from the server
  async function refresh() {
    try {
      setAvailability(await api.getAvailability());
      setSlots(await api.getSlots());
      // My reservation is remembered in the browser. If the server no longer knows it, forget it.
      const id = localStorage.getItem("reservationId");
      setReservation(id ? await api.getReservation(id).catch(() => null) : null);
    } catch (e) {
      setError(e.message);
    }
  }

  // Load when the page opens, then again every 5 seconds
  useEffect(() => {
    refresh();
    api.getLayout().then(setLayout).catch((e) => setError(e.message));
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, []);

  // Run one action (reserve, arrive, ...), show any error, then refresh
  async function run(action) {
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e.message);
    }
    refresh();
  }

  function handleReserve(plate, vehicleClass) {
    run(async () => {
      const result = await api.reserve(plate, vehicleClass);
      localStorage.setItem("reservationId", result.reservation_id);
    });
  }

  const active = reservation && reservation.status === "active" ? reservation : null;
  const mySlot = active && slots.find((s) => s.id === active.slot_id);
  const onTheWay = mySlot && mySlot.status === "reserved"; // reserved, not parked yet

  // Get the route once for each reservation
  const activeId = active ? active.reservation_id : null;
  useEffect(() => {
    setRoute(null);
    if (activeId) api.getRoute(activeId).then(setRoute).catch(() => {});
  }, [activeId]);

  const guide = useGuidance(onTheWay ? route : null);

  return (
    <div className="page">
      <h1>Smart Parking</h1>
      <p className="subtitle">Tell us your vehicle size and we reserve a slot that fits.</p>

      {error && <div className="error">{error}</div>}

      <h2>Available slots</h2>
      <Availability availability={availability} />

      {active ? (
        <Reservation reservation={active} slotStatus={mySlot?.status} guide={guide}
                     routeLength={route?.length_m} run={run} api={api} />
      ) : (
        <ReserveForm onReserve={handleReserve} />
      )}

      <div className="map-head">
        <h2>Parking lot</h2>
        <div className="zoom">
          <button className="grey small" onClick={() => setZoom(Math.max(1, zoom - 0.5))}>-</button>
          Zoom
          <button className="grey small" onClick={() => setZoom(Math.min(3, zoom + 0.5))}>+</button>
        </div>
      </div>
      <LotMap layout={layout} slots={slots} mySlotId={active?.slot_id}
              route={onTheWay ? route : null} dot={guide.dot} zoom={zoom} />
      <div className="legend">
        <span className="swatch free" /> free <span className="swatch reserved" /> reserved{" "}
        <span className="swatch occupied" /> parked car <span className="swatch route" /> your route.
        Roads are one-way (arrows).
      </div>
    </div>
  );
}
