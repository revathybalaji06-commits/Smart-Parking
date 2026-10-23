// Show the current slot, route instructions, and actions for the driver.
export default function Reservation({
  reservation,
  slotStatus,
  guide,
  routeLength,
  run,
  api,
}) {
  const reservationId = reservation.reservation_id;
  const isReserved = slotStatus === "reserved";
  const isOccupied = slotStatus === "occupied";

  return (
    <section className="panel">
      <h2>Your reservation</h2>
      <p className="slot-name">Slot {reservation.label}</p>
      <p>
        Plate {reservation.plate}
        {isReserved && " · held for 15 minutes, go to your slot"}
        {isOccupied && " · you are parked"}
      </p>

      {isReserved && guide.steps.length > 0 && (
        <div className="guide">
          <h3>
            Directions to {reservation.label} · {routeLength} m
          </h3>
          <ol>
            {guide.steps.map((step, index) => {
              let stepClass = "";
              if (index === guide.stepIndex) stepClass = "current";
              if (index < guide.stepIndex) stepClass = "done";

              return (
                <li key={index} className={stepClass}>
                  {step.text}
                </li>
              );
            })}
          </ol>

          <div className="buttons">
            <button onClick={guide.startOrPause}>
              {guide.playing ? "Pause" : "Start guidance"}
            </button>
            <button className="grey" onClick={guide.nextStep}>
              Next step
            </button>
            <button className="grey" onClick={guide.replay}>
              Replay
            </button>
          </div>
        </div>
      )}

      {isReserved && (
        <div className="buttons">
          <button onClick={() => run(() => api.arrive(reservationId))}>
            I have arrived
          </button>
          <button
            className="grey"
            onClick={() => run(() => api.cancel(reservationId))}
          >
            Cancel
          </button>
        </div>
      )}

      {isOccupied && (
        <div className="buttons">
          <button onClick={() => run(() => api.depart(reservationId))}>
            I am leaving
          </button>
        </div>
      )}
    </section>
  );
}
