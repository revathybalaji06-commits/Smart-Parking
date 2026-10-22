import { useEffect, useState } from "react";
import * as api from "./api";
import LotMap, { positionAt } from "./LotMap";

const CLASSES = [
  { id: 1, name: "Compact", note: "small cars, hatchbacks" },
  { id: 2, name: "Sedan", note: "mid-size sedans, coupes" },
  { id: 3, name: "SUV", note: "SUVs, minivans" },
  { id: 4, name: "Full-Size", note: "large and luxury cars" },
];

export default function App() {
  const [availability, setAvailability] = useState(null);
  const [slots, setSlots] = useState([]);
  const [reservation, setReservation] = useState(null);
  const [plate, setPlate] = useState("");
  const [vehicleClass, setVehicleClass] = useState(2);
  const [error, setError] = useState("");
  const [layout, setLayout] = useState(null); // roads, gates, trees
  const [route, setRoute] = useState(null); // the way from the gate to my slot
  const [progress, setProgress] = useState(0); // how far the dot has travelled (metres)
  const [target, setTarget] = useState(0); // where the dot is heading
  const [zoom, setZoom] = useState(1);

  // Reload everything from the server
  async function refresh() {
    try {
      setAvailability(await api.getAvailability());
      setSlots(await api.getSlots());
    } catch (e) {
      setError(e.message);
    }
    // Our saved reservation. If the server no longer knows it, forget it.
    const savedId = localStorage.getItem("reservationId");
    if (savedId) {
      try {
        setReservation(await api.getReservation(savedId));
      } catch (e) {
        localStorage.removeItem("reservationId");
        setReservation(null);
      }
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

  function handleReserve(event) {
    event.preventDefault();
    run(async () => {
      const result = await api.reserve(plate, vehicleClass);
      localStorage.setItem("reservationId", result.reservation_id);
    });
  }

  // My slot's current status tells us which buttons to show
  const mySlot = reservation && slots.find((s) => s.id === reservation.slot_id);
  const hasActive = reservation && reservation.status === "active";
  const guiding = hasActive && mySlot?.status === "reserved"; // on the way to the slot

  // Get the route once for each reservation
  const reservationId = hasActive ? reservation.reservation_id : null;
  useEffect(() => {
    setRoute(null);
    setProgress(0);
    setTarget(0);
    if (!reservationId) return;
    api.getRoute(reservationId).then(setRoute).catch(() => {});
  }, [reservationId]);

  // Move the dot toward the target a little every 40 ms (about 40 km/h)
  useEffect(() => {
    if (progress >= target) return;
    const timer = setTimeout(() => setProgress((p) => Math.min(p + 0.45, target)), 40);
    return () => clearTimeout(timer);
  }, [progress, target]);

  // Which step are we on? A step is done when the dot has reached its end.
  const steps = route ? route.steps : [];
  let stepIndex = steps.findIndex((st) => st.distance > progress + 0.01);
  if (stepIndex === -1) stepIndex = steps.length - 1;

  const moving = progress < target;
  const dot = route && guiding ? positionAt(route, progress) : null;

  function startOrPause() {
    setTarget(moving ? progress : route.distances[route.distances.length - 1]);
  }
  function nextStep() {
    setTarget(steps[stepIndex].distance);
  }
  function replay() {
    setProgress(0);
    setTarget(0);
  }

  return (
    <div className="page">
      <h1>Smart Parking</h1>
      <p className="subtitle">Tell us your vehicle size and we reserve a slot that fits.</p>

      {error && <div className="error">{error}</div>}

      {/* 1. How many slots are free */}
      <h2>Available slots</h2>
      {availability && (
        <div className="cards">
          <div className="card total">
            <div className="big">{availability.lot.free}</div>
            <div>free of {availability.lot.max}</div>
          </div>
          {availability.classes.map((c) => (
            <div className="card" key={c.class}>
              <div className="big">{c.free}</div>
              <div>{c.name} free of {c.max}</div>
            </div>
          ))}
        </div>
      )}

      {/* 2. Reserve a slot, or manage the current reservation */}
      {!hasActive ? (
        <form className="panel" onSubmit={handleReserve}>
          <h2>Reserve a slot</h2>
          <label>
            Number plate
            <input
              value={plate}
              onChange={(e) => setPlate(e.target.value)}
              placeholder="TN37AB1234"
            />
          </label>
          <label>
            Vehicle size
            <select value={vehicleClass} onChange={(e) => setVehicleClass(Number(e.target.value))}>
              {CLASSES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.note})
                </option>
              ))}
            </select>
          </label>
          <button type="submit">Reserve</button>
        </form>
      ) : (
        <div className="panel">
          <h2>Your reservation</h2>
          <p className="slot-name">Slot {reservation.label}</p>
          <p>
            Plate {reservation.plate}
            {mySlot?.status === "reserved" && " · held for 15 minutes, go to your slot"}
            {mySlot?.status === "occupied" && " · you are parked"}
          </p>
          {guiding && route && (
            <div className="guide">
              <h3>
                Directions to {reservation.label} · {route.length_m} m
              </h3>
              <ol>
                {steps.map((st, i) => (
                  <li key={i} className={i === stepIndex ? "current" : i < stepIndex ? "done" : ""}>
                    {st.text}
                  </li>
                ))}
              </ol>
              <div className="buttons">
                <button onClick={startOrPause}>{moving ? "Pause" : "Start guidance"}</button>
                <button className="grey" onClick={nextStep}>Next step</button>
                <button className="grey" onClick={replay}>Replay</button>
              </div>
            </div>
          )}
          {mySlot?.status === "reserved" && (
            <div className="buttons">
              <button onClick={() => run(() => api.arrive(reservation.reservation_id))}>
                I have arrived
              </button>
              <button className="grey" onClick={() => run(() => api.cancel(reservation.reservation_id))}>
                Cancel
              </button>
            </div>
          )}
          {mySlot?.status === "occupied" && (
            <div className="buttons">
              <button onClick={() => run(() => api.depart(reservation.reservation_id))}>
                I am leaving
              </button>
            </div>
          )}
        </div>
      )}

      {/* 3. Map of the lot */}
      <div className="map-head">
        <h2>Parking lot</h2>
        <div className="zoom">
          <button className="grey small" onClick={() => setZoom(Math.max(1, zoom - 0.5))}>-</button>
          <span>Zoom</span>
          <button className="grey small" onClick={() => setZoom(Math.min(3, zoom + 0.5))}>+</button>
        </div>
      </div>
      <LotMap layout={layout} slots={slots} mySlotId={hasActive ? reservation.slot_id : null}
              route={guiding ? route : null} dot={dot} zoom={zoom} />
      <div className="legend">
        <span className="dot free" /> free <span className="dot reserved" /> reserved{" "}
        <span className="dot occupied" /> parked car <span className="dot mine" /> your slot
        <span className="dot routekey" /> your route. Roads are one-way (arrows).
      </div>
    </div>
  );
}
