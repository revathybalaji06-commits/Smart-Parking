// Draw the parking lot as an SVG map. One map unit is about one metre.

const BAY_COLOURS = {
  free: "#bbf7d0",
  reserved: "#fde68a",
  occupied: "#d1d5db",
};
const CAR_COLOURS = [
  "#64748b",
  "#b91c1c",
  "#1e40af",
  "#0f766e",
  "#a16207",
  "#7c3aed",
];

function Bay({ slot, belongsToDriver }) {
  const { x, y, width, height, status, label, id } = slot;
  const carColour = CAR_COLOURS[id % CAR_COLOURS.length];

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={BAY_COLOURS[status]}
        stroke="white"
        strokeWidth="0.25"
      />

      {status === "occupied" ? (
        <rect
          x={x + 0.5}
          y={y + 0.5}
          width={width - 1}
          height={height - 1}
          rx="0.9"
          fill={carColour}
        />
      ) : (
        <text
          x={x + width / 2}
          y={y + height / 2}
          fontSize="1.3"
          textAnchor="middle"
          dominantBaseline="central"
          fill="#14532d"
          fontWeight="600"
        >
          {label}
        </text>
      )}

      {belongsToDriver && (
        <rect
          className="pulse"
          x={x - 0.4}
          y={y - 0.4}
          width={width + 0.8}
          height={height + 0.8}
          fill="none"
          stroke="#2563eb"
          strokeWidth="0.6"
        />
      )}
    </g>
  );
}

function Road({ start, end, nodes, roadWidth }) {
  const [startX, startY] = nodes[start];
  const [endX, endY] = nodes[end];
  const middleX = (startX + endX) / 2;
  const middleY = (startY + endY) / 2;

  return (
    <g>
      <line
        x1={startX}
        y1={startY}
        x2={endX}
        y2={endY}
        stroke="#4b5159"
        strokeWidth={roadWidth}
        strokeLinecap="square"
      />
      <polyline
        points={`${startX},${startY} ${middleX},${middleY} ${endX},${endY}`}
        fill="none"
        stroke="white"
        strokeWidth="0.2"
        strokeDasharray="1.6 1.6"
        markerMid="url(#arrow)"
      />
    </g>
  );
}

function Building({ building }) {
  const [name, x, y, width, height] = building;

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx="0.6" fill="#9aa5b1" />
      <text
        x={x + width / 2}
        y={y + height / 2}
        fontSize="1.8"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#1f2933"
      >
        {name}
      </text>
    </g>
  );
}

function Tree({ tree }) {
  const [x, y, radius] = tree;
  return <circle cx={x} cy={y} r={radius} fill="#43a047" />;
}

function Gate({ name, colour, position }) {
  const [x, y] = position;

  return (
    <g>
      <line
        x1={x - 3.5}
        y1={y - 2}
        x2={x + 3.5}
        y2={y - 2}
        stroke={colour}
        strokeWidth="0.9"
      />
      <rect
        x={x - 6}
        y={y + 2.4}
        width="12"
        height="3.4"
        rx="0.5"
        fill={colour}
      />
      <text
        x={x}
        y={y + 4.1}
        fontSize="1.9"
        textAnchor="middle"
        dominantBaseline="central"
        fill="white"
        fontWeight="700"
      >
        {name}
      </text>
    </g>
  );
}

export default function LotMap({ layout, slots, mySlotId, route, dot, zoom }) {
  if (!layout) return null;

  const { nodes, edges, trees, buildings } = layout;
  const mapStyle = { width: `${zoom * 100}%` };
  const scrollStyle = { maxHeight: zoom > 1 ? "75vh" : "none" };
  const gates = [
    { name: "ENTRY", colour: "#16a34a" },
    { name: "EXIT", colour: "#dc2626" },
  ];

  return (
    <div className="map-scroll" style={scrollStyle}>
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} style={mapStyle}>
        <defs>
          <marker
            id="arrow"
            markerUnits="userSpaceOnUse"
            markerWidth="3"
            markerHeight="3"
            refX="1.5"
            refY="1.5"
            orient="auto"
          >
            <path d="M0,0 L3,1.5 L0,3 z" fill="white" />
          </marker>
        </defs>

        <rect width={layout.width} height={layout.height} fill="#e5e7e2" />

        {edges.map(([start, end]) => (
          <g key={`${start}-${end}`}>
            <Road
              start={start}
              end={end}
              nodes={nodes}
              roadWidth={layout.road_width}
            />
          </g>
        ))}

        {buildings.map((building) => (
          <Building key={building[0]} building={building} />
        ))}

        {trees.map((tree) => (
          <Tree key={`${tree[0]}-${tree[1]}`} tree={tree} />
        ))}

        {gates.map((gate) => (
          <Gate
            key={gate.name}
            name={gate.name}
            colour={gate.colour}
            position={nodes[gate.name]}
          />
        ))}

        {slots.map((slot) => (
          <Bay
            key={slot.id}
            slot={slot}
            belongsToDriver={slot.id === mySlotId}
          />
        ))}

        {route && (
          <polyline
            points={route.points.map((point) => point.join(",")).join(" ")}
            fill="none"
            stroke="#2563eb"
            strokeWidth="1.2"
            strokeLinejoin="round"
            strokeDasharray="2.4 1.6"
          />
        )}

        {dot && (
          <circle
            cx={dot[0]}
            cy={dot[1]}
            r="1.6"
            fill="#2563eb"
            stroke="white"
            strokeWidth="0.5"
          />
        )}
      </svg>
    </div>
  );
}
