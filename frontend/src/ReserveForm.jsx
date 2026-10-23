import { useState } from "react";

const VEHICLE_CLASSES = [
  { number: 1, name: "Compact", examples: "small cars, hatchbacks" },
  { number: 2, name: "Sedan", examples: "mid-size sedans, coupes" },
  { number: 3, name: "SUV", examples: "SUVs, minivans" },
  { number: 4, name: "Full-Size", examples: "large and luxury cars" },
];

export default function ReserveForm({ onReserve }) {
  const [plate, setPlate] = useState("");
  const [vehicleClass, setVehicleClass] = useState(2);

  function submitForm(event) {
    event.preventDefault();
    onReserve(plate, vehicleClass);
  }

  return (
    <form className="panel" onSubmit={submitForm}>
      <h2>Reserve a slot</h2>

      <label>
        Number plate
        <input
          value={plate}
          onChange={(event) => setPlate(event.target.value)}
          placeholder="TN37AB1234"
        />
      </label>

      <label>
        Vehicle size
        <select
          value={vehicleClass}
          onChange={(event) => setVehicleClass(Number(event.target.value))}
        >
          {VEHICLE_CLASSES.map((vehicle) => (
            <option key={vehicle.number} value={vehicle.number}>
              {vehicle.name} ({vehicle.examples})
            </option>
          ))}
        </select>
      </label>

      <button type="submit">Reserve</button>
    </form>
  );
}
