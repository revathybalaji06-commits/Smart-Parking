import { useEffect, useRef } from "react";

// Colours for the parked cars (a car's colour is picked from its slot number)
const CAR_COLOURS = ["#64748b", "#b91c1c", "#1e40af", "#0f766e", "#a16207", "#475569", "#7c3aed"];

// Where is the dot after travelling `distance` along the route?
export function positionAt(route, distance) {
  const { points, distances } = route;
  for (let i = 1; i < points.length; i++) {
    if (distance <= distances[i]) {
      const part = (distance - distances[i - 1]) / (distances[i] - distances[i - 1]);
      return {
        x: points[i - 1].x + (points[i].x - points[i - 1].x) * part,
        y: points[i - 1].y + (points[i].y - points[i - 1].y) * part,
      };
    }
  }
  return points[points.length - 1];
}

// One parking bay: the painted box, and a car inside it if the bay is taken
function Bay({ slot, mine }) {
  const { x, y, width, height, status, label, id } = slot;
  const fill = status === "free" ? "#bbf7d0" : status === "reserved" ? "#fde68a" : "#d1d5db";
  const tall = height > width; // cars in "Row 2..6" point up and down; in rows 1 and 7 sideways
  const car = (
    <g>
      <rect x={x + 0.45} y={y + 0.45} width={width - 0.9} height={height - 0.9} rx="0.9"
            fill={CAR_COLOURS[id % CAR_COLOURS.length]} />
      <rect x={tall ? x + 0.9 : x + width * 0.3} y={tall ? y + height * 0.3 : y + 0.9}
            width={tall ? width - 1.8 : width * 0.4} height={tall ? height * 0.4 : height - 1.8}
            rx="0.6" fill="#0f172a" opacity="0.55" />
    </g>
  );
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#ffffff" strokeWidth="0.25" />
      {status === "occupied" && car}
      {status !== "occupied" && (
        <text x={x + width / 2} y={y + height / 2} fontSize="1.3" textAnchor="middle"
              dominantBaseline="central" fill="#14532d" fontWeight="600">
          {label}
        </text>
      )}
      {mine && (
        <rect className="pulse" x={x - 0.4} y={y - 0.4} width={width + 0.8} height={height + 0.8}
              fill="none" stroke="#2563eb" strokeWidth="0.6" />
      )}
    </g>
  );
}

// A small white arrow showing which way the one-way road goes
function Arrow({ x, y, angle }) {
  return (
    <polygon points="-1.1,-1 1,0 -1.1,1" fill="#ffffff" opacity="0.75"
             transform={`translate(${x} ${y}) rotate(${angle})`} />
  );
}

export default function LotMap({ layout, slots, mySlotId, route, dot, zoom }) {
  const box = useRef(null);

  // While zoomed in, keep the moving dot in the middle of the view
  useEffect(() => {
    if (!dot || !box.current || zoom === 1 || !layout) return;
    const el = box.current;
    const svg = el.firstChild;
    const scale = svg.clientWidth / layout.width;
    el.scrollTo({
      left: dot.x * scale - el.clientWidth / 2,
      top: dot.y * scale - el.clientHeight / 2,
      behavior: "smooth",
    });
  }, [dot, zoom, layout]);

  if (!layout) return <p>Loading map...</p>;

  // Row names: a small label at the end of each row
  const rows = {};
  slots.forEach((s) => {
    const r = (rows[s.row_name] = rows[s.row_name] || { x1: 1e9, y1: 1e9, x2: 0, y2: 0 });
    r.x1 = Math.min(r.x1, s.x);
    r.y1 = Math.min(r.y1, s.y);
    r.x2 = Math.max(r.x2, s.x + s.width);
    r.y2 = Math.max(r.y2, s.y + s.height);
  });

  const { entry, exit } = layout.gates;
  const mySlot = slots.find((s) => s.id === mySlotId);

  return (
    <div className="map-scroll" ref={box} style={{ maxHeight: zoom > 1 ? "75vh" : "none" }}>
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} style={{ width: `${zoom * 100}%` }}
           role="img" aria-label="Map of the parking lot">
        {/* ground and fence */}
        <rect width={layout.width} height={layout.height} fill="#e5e7e2" />
        <rect x="0.4" y="0.4" width={layout.width - 0.8} height={layout.height - 0.8} fill="none"
              stroke="#6b7280" strokeWidth="0.5" strokeDasharray="1 0.6" />

        {/* roads, centre lines and direction arrows */}
        {layout.edges.map((e, i) => (
          <line key={"road" + i} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} stroke="#4b5159"
                strokeWidth={layout.road_width} strokeLinecap="square" />
        ))}
        {layout.edges.map((e, i) => (
          <line key={"mid" + i} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} stroke="#ffffff"
                strokeWidth="0.2" strokeDasharray="1.6 1.6" opacity="0.6" />
        ))}
        {layout.edges.map((e, i) => {
          const length = Math.hypot(e.x2 - e.x1, e.y2 - e.y1);
          const angle = (Math.atan2(e.y2 - e.y1, e.x2 - e.x1) * 180) / Math.PI;
          const arrows = [];
          for (let d = 8; d < length - 4; d += 12) {
            arrows.push(<Arrow key={d} x={e.x1 + ((e.x2 - e.x1) * d) / length}
                               y={e.y1 + ((e.y2 - e.y1) * d) / length} angle={angle} />);
          }
          return <g key={"arrows" + i}>{arrows}</g>;
        })}

        {/* buildings and trees */}
        {layout.buildings.map((b) => (
          <g key={b.name}>
            <rect x={b.x} y={b.y} width={b.w} height={b.h} rx="0.6" fill="#9aa5b1" stroke="#64748b" strokeWidth="0.3" />
            <text x={b.x + b.w / 2} y={b.y + b.h / 2} fontSize="1.8" textAnchor="middle"
                  dominantBaseline="central" fill="#1f2933">{b.name}</text>
          </g>
        ))}
        {layout.trees.map((t, i) => (
          <g key={"tree" + i}>
            <circle cx={t.x} cy={t.y} r={t.r} fill="#2e7d32" />
            <circle cx={t.x - 0.3} cy={t.y - 0.3} r={t.r * 0.6} fill="#4caf50" />
          </g>
        ))}

        {/* the gates: a barrier arm, a booth and a sign */}
        {[["ENTRY", entry, "#16a34a"], ["EXIT", exit, "#dc2626"]].map(([name, g, colour]) => (
          <g key={name}>
            <rect x={g.x + 4} y={g.y - 4} width="3" height="4" fill="#cbd5e1" stroke="#64748b" strokeWidth="0.25" />
            <line x1={g.x - 3.5} y1={g.y - 2} x2={g.x + 3.5} y2={g.y - 2} stroke={colour} strokeWidth="0.9" />
            <rect x={g.x - 6} y={g.y + 2.4} width="12" height="3.4" rx="0.5" fill={colour} />
            <text x={g.x} y={g.y + 4.1} fontSize="1.9" textAnchor="middle" dominantBaseline="central"
                  fill="#ffffff" fontWeight="700">{name === "ENTRY" ? "ENTRY" : "EXIT"}</text>
          </g>
        ))}

        {/* the parking bays */}
        {slots.map((s) => <Bay key={s.id} slot={s} mine={s.id === mySlotId} />)}

        {/* row names */}
        {Object.entries(rows).map(([name, r]) => {
          const horizontal = r.x2 - r.x1 > r.y2 - r.y1;
          return horizontal ? (
            <text key={name} x={r.x2 + 0.8} y={(r.y1 + r.y2) / 2} fontSize="1.4" dominantBaseline="central"
                  fill="#374151" fontWeight="600">{name}</text>
          ) : (
            <text key={name} x={(r.x1 + r.x2) / 2} y={r.y1 - 1} fontSize="1.4" textAnchor="middle"
                  fill="#374151" fontWeight="600">{name}</text>
          );
        })}

        {/* the route and the moving dot */}
        {route && (
          <g>
            <polyline points={route.points.map((p) => `${p.x},${p.y}`).join(" ")} fill="none"
                      stroke="#ffffff" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
            <polyline className="route-line" points={route.points.map((p) => `${p.x},${p.y}`).join(" ")}
                      fill="none" stroke="#2563eb" strokeWidth="1.2" strokeLinejoin="round"
                      strokeLinecap="round" strokeDasharray="2.4 1.6" />
          </g>
        )}
        {mySlot && !route && (
          <rect className="pulse" x={mySlot.x - 0.4} y={mySlot.y - 0.4} width={mySlot.width + 0.8}
                height={mySlot.height + 0.8} fill="none" stroke="#2563eb" strokeWidth="0.6" />
        )}
        {dot && (
          <g>
            <circle className="dot-ring" cx={dot.x} cy={dot.y} r="2.6" fill="#2563eb" opacity="0.25" />
            <circle cx={dot.x} cy={dot.y} r="1.5" fill="#2563eb" stroke="#ffffff" strokeWidth="0.5" />
          </g>
        )}
      </svg>
    </div>
  );
}
