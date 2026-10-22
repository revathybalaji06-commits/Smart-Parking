// Draws the parking lot as a map (SVG). One unit on the map is about one metre.

const BAY_COLOURS = { free: "#bbf7d0", reserved: "#fde68a", occupied: "#d1d5db" };
const CAR_COLOURS = ["#64748b", "#b91c1c", "#1e40af", "#0f766e", "#a16207", "#7c3aed"];

// One parking bay. A taken bay shows a car, a free one shows its label.
function Bay({ slot, mine }) {
  const { x, y, width, height, status, label, id } = slot;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={BAY_COLOURS[status]}
            stroke="white" strokeWidth="0.25" />
      {status === "occupied" ? (
        <rect x={x + 0.5} y={y + 0.5} width={width - 1} height={height - 1} rx="0.9"
              fill={CAR_COLOURS[id % CAR_COLOURS.length]} />
      ) : (
        <text x={x + width / 2} y={y + height / 2} fontSize="1.3" textAnchor="middle"
              dominantBaseline="central" fill="#14532d" fontWeight="600">{label}</text>
      )}
      {mine && (
        <rect className="pulse" x={x - 0.4} y={y - 0.4} width={width + 0.8} height={height + 0.8}
              fill="none" stroke="#2563eb" strokeWidth="0.6" />
      )}
    </g>
  );
}

export default function LotMap({ layout, slots, mySlotId, route, dot, zoom }) {
  if (!layout) return null;
  const { nodes, edges, trees, buildings } = layout;

  return (
    <div className="map-scroll" style={{ maxHeight: zoom > 1 ? "75vh" : "none" }}>
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} style={{ width: `${zoom * 100}%` }}>
        {/* a small arrow, used to show which way each road goes */}
        <defs>
          <marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="3" markerHeight="3"
                  refX="1.5" refY="1.5" orient="auto">
            <path d="M0,0 L3,1.5 L0,3 z" fill="white" />
          </marker>
        </defs>

        <rect width={layout.width} height={layout.height} fill="#e5e7e2" />

        {/* roads: a thick grey line, then a dashed white line with an arrow in the middle */}
        {edges.map(([from, to]) => {
          const [x1, y1] = nodes[from];
          const [x2, y2] = nodes[to];
          return (
            <g key={from + to}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#4b5159"
                    strokeWidth={layout.road_width} strokeLinecap="square" />
              <polyline points={`${x1},${y1} ${(x1 + x2) / 2},${(y1 + y2) / 2} ${x2},${y2}`}
                        fill="none" stroke="white" strokeWidth="0.2" strokeDasharray="1.6 1.6"
                        markerMid="url(#arrow)" />
            </g>
          );
        })}

        {buildings.map(([name, x, y, w, h]) => (
          <g key={name}>
            <rect x={x} y={y} width={w} height={h} rx="0.6" fill="#9aa5b1" />
            <text x={x + w / 2} y={y + h / 2} fontSize="1.8" textAnchor="middle"
                  dominantBaseline="central" fill="#1f2933">{name}</text>
          </g>
        ))}
        {trees.map(([x, y, r]) => <circle key={`${x},${y}`} cx={x} cy={y} r={r} fill="#43a047" />)}

        {/* the two gates */}
        {[["ENTRY", "#16a34a"], ["EXIT", "#dc2626"]].map(([name, colour]) => {
          const [x, y] = nodes[name];
          return (
            <g key={name}>
              <line x1={x - 3.5} y1={y - 2} x2={x + 3.5} y2={y - 2} stroke={colour} strokeWidth="0.9" />
              <rect x={x - 6} y={y + 2.4} width="12" height="3.4" rx="0.5" fill={colour} />
              <text x={x} y={y + 4.1} fontSize="1.9" textAnchor="middle" dominantBaseline="central"
                    fill="white" fontWeight="700">{name}</text>
            </g>
          );
        })}

        {slots.map((slot) => <Bay key={slot.id} slot={slot} mine={slot.id === mySlotId} />)}

        {/* the route and the moving dot */}
        {route && (
          <polyline points={route.points.map((p) => p.join(",")).join(" ")} fill="none"
                    stroke="#2563eb" strokeWidth="1.2" strokeLinejoin="round" strokeDasharray="2.4 1.6" />
        )}
        {dot && <circle cx={dot[0]} cy={dot[1]} r="1.6" fill="#2563eb" stroke="white" strokeWidth="0.5" />}
      </svg>
    </div>
  );
}
