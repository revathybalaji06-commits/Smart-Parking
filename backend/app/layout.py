"""The parking lot map: roads, gates and decorations. Same numbers as db/generate_seed.py.

Units are roughly metres. x goes right, y goes DOWN. All roads are ONE-WAY
(cars drive on the left, so the loop runs clockwise):

    ENTRY -> up the left road -> along the top road -> down the right road -> EXIT
    with two cross aisles (y=36 and y=60) that cut across from the left road to the right road.
"""

# Junctions: places where roads meet or end
NODES = {
    "ENTRY": (14, 86),
    "J2": (14, 60),
    "J1": (14, 36),
    "TL": (14, 12),
    "TR": (76, 12),
    "R1": (76, 36),
    "R2": (76, 60),
    "EXIT": (76, 86),
}

# One-way road pieces: (from, to). A car can only drive in this direction.
EDGES = [
    ("ENTRY", "J2"), ("J2", "J1"), ("J1", "TL"),   # left road, going up
    ("TL", "TR"),                                  # top road, going right
    ("TR", "R1"), ("R1", "R2"), ("R2", "EXIT"),    # right road, going down
    ("J1", "R1"),                                  # cross aisle 1, going right
    ("J2", "R2"),                                  # cross aisle 2, going right
]

# The map sent to the frontend. Trees are (x, y, radius), buildings are (name, x, y, width, height).
LAYOUT = {
    "width": 90,
    "height": 92,
    "road_width": 7,
    "nodes": NODES,
    "edges": EDGES,
    "trees": [(25, 24, 1.8), (38, 24, 1.8), (53, 24, 1.8), (66, 24, 1.8),
              (24, 48, 1.8), (40, 48, 1.8), (56, 48, 1.8), (68, 48, 1.8),
              (60, 66, 1.8), (66, 66, 1.8)],
    "buildings": [("Academic Block", 22, 0.5, 46, 6), ("Security", 38, 76, 14, 8)],
}
