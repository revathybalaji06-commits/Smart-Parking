// The driver's current reservation: directions while driving to the slot,
// then the arrive / leave / cancel buttons.
export default function Reservation({ reservation, slotStatus, guide, routeLength, run, api }) {
  const id = reservation.reservation_id;
  return (
    <div className="panel">
      <h2>Your reservation</h2>
      <p className="slot-name">Slot {reservation.label}</p>
      <p>
        Plate {reservation.plate}
        {slotStatus === "reserved" && " · held for 15 minutes, go to your slot"}
        {slotStatus === "occupied" && " · you are parked"}
      </p>

      {slotStatus === "reserved" && guide.steps.length > 0 && (
        <div className="guide">
          <h3>Directions to {reservation.label} · {routeLength} m</h3>
          <ol>
            {guide.steps.map((step, i) => (
              <li key={i} className={i === guide.stepIndex ? "current" : i < guide.stepIndex ? "done" : ""}>
                {step.text}
              </li>
            ))}
          </ol>
          <div className="buttons">
            <button onClick={guide.startOrPause}>{guide.playing ? "Pause" : "Start guidance"}</button>
            <button className="grey" onClick={guide.nextStep}>Next step</button>
            <button className="grey" onClick={guide.replay}>Replay</button>
          </div>
        </div>
      )}

      {slotStatus === "reserved" && (
        <div className="buttons">
          <button onClick={() => run(() => api.arrive(id))}>I have arrived</button>
          <button className="grey" onClick={() => run(() => api.cancel(id))}>Cancel</button>
        </div>
      )}
      {slotStatus === "occupied" && (
        <div className="buttons">
          <button onClick={() => run(() => api.depart(id))}>I am leaving</button>
        </div>
      )}
    </div>
  );
}
