"""The parking lot map: roads, gates and decorations. Same numbers as db/generate_seed.py.

Units are roughly metres. x goes right, y goes DOWN. All roads are ONE-WAY
(cars drive on the left, so the loop runs clockwise):

    ENTRY -> up the left road -> along the top road -> down the right road -> EXIT
    with two cross aisles (y=36 and y=60) that cut across from the left road to the right road.
"""

WIDTH, HEIGHT = 90, 92
ROAD_WIDTH = 7

# Junctions (places where roads meet or end)
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

# Only for drawing
TREES = [(25, 24, 1.8), (38, 24, 1.8), (53, 24, 1.8), (66, 24, 1.8),
         (24, 48, 1.8), (40, 48, 1.8), (56, 48, 1.8), (68, 48, 1.8),
         (60, 66, 1.8), (66, 66, 1.8), (21, 20, 1.5), (68, 66, 1.5)]
BUILDINGS = [
    {"name": "Academic Block", "x": 22, "y": 0.5, "w": 46, "h": 6},
    {"name": "Security", "x": 38, "y": 76, "w": 14, "h": 8},
]


def get_layout():
    """Everything the frontend needs to draw the lot."""
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "road_width": ROAD_WIDTH,
        "edges": [
            {"from": a, "to": b, "x1": NODES[a][0], "y1": NODES[a][1],
             "x2": NODES[b][0], "y2": NODES[b][1]}
            for a, b in EDGES
        ],
        "gates": {
            "entry": {"x": NODES["ENTRY"][0], "y": NODES["ENTRY"][1]},
            "exit": {"x": NODES["EXIT"][0], "y": NODES["EXIT"][1]},
        },
        "trees": [{"x": x, "y": y, "r": r} for x, y, r in TREES],
        "buildings": BUILDINGS,
    }
