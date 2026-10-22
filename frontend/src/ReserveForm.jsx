import { useState } from "react";

const CLASSES = [
  { id: 1, name: "Compact", note: "small cars, hatchbacks" },
  { id: 2, name: "Sedan", note: "mid-size sedans, coupes" },
  { id: 3, name: "SUV", note: "SUVs, minivans" },
  { id: 4, name: "Full-Size", note: "large and luxury cars" },
];

// The form where the driver enters the plate and the vehicle size
export default function ReserveForm({ onReserve }) {
  const [plate, setPlate] = useState("");
  const [vehicleClass, setVehicleClass] = useState(2);

  function handleSubmit(event) {
    event.preventDefault();
    onReserve(plate, vehicleClass);
  }

  return (
    <form className="panel" onSubmit={handleSubmit}>
      <h2>Reserve a slot</h2>
      <label>
        Number plate
        <input value={plate} onChange={(e) => setPlate(e.target.value)} placeholder="TN37AB1234" />
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
  );
}
