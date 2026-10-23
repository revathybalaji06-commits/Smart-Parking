// Show the free-space count for the lot and for each exact vehicle class.
export default function Availability({ availability }) {
  if (availability === null) {
    return null;
  }

  return (
    <div className="cards">
      <div className="card total">
        <div className="big">{availability.lot.free}</div>
        <div>free of {availability.lot.max}</div>
      </div>

      {availability.classes.map((vehicleClass) => (
        <div className="card" key={vehicleClass.class}>
          <div className="big">{vehicleClass.free}</div>
          <div>
            {vehicleClass.name} free of {vehicleClass.max}
          </div>
        </div>
      ))}
    </div>
  );
}
