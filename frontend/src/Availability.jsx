// How many slots are free: in total and for each size class
export default function Availability({ availability }) {
  if (!availability) return null;
  return (
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
  );
}
