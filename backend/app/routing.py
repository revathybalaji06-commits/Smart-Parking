"""The map of the lot, and the route from the entry gate to a slot.

Units are roughly metres. x goes right, y goes DOWN. All roads are ONE-WAY
(cars drive on the left, so the loop runs clockwise):

    ENTRY -> up the left road -> along the top road -> down the right road -> EXIT
    plus two cross aisles (y=36 and y=60) from the left road to the right road.
"""
import math

# Junctions: places where roads meet or end
NODES = {
    "ENTRY": (14, 86), "J2": (14, 60), "J1": (14, 36), "TL": (14, 12),
    "TR": (76, 12), "R1": (76, 36), "R2": (76, 60), "EXIT": (76, 86),
}

# One-way road pieces: (from, to). A car can only drive in this direction.
EDGES = [
    ("ENTRY", "J2"), ("J2", "J1"), ("J1", "TL"),   # left road, going up
    ("TL", "TR"),                                  # top road, going right
    ("TR", "R1"), ("R1", "R2"), ("R2", "EXIT"),    # right road, going down
    ("J1", "R1"), ("J2", "R2"),                    # the two cross aisles, going right
]

# Sent to the website so it can draw the lot.
# Trees are (x, y, radius). Buildings are (name, x, y, width, height).
LAYOUT = {
    "width": 90, "height": 92, "road_width": 7, "nodes": NODES, "edges": EDGES,
    "trees": [(25, 24, 1.8), (38, 24, 1.8), (53, 24, 1.8), (66, 24, 1.8), (24, 48, 1.8),
              (40, 48, 1.8), (56, 48, 1.8), (68, 48, 1.8), (60, 66, 1.8), (66, 66, 1.8)],
    "buildings": [("Academic Block", 22, 0.5, 46, 6), ("Security", 38, 76, 14, 8)],
}


def length(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def shortest_path(start, goal):
    """The shortest way along the one-way roads, as a list of junction names.

    We go over all the road pieces again and again. Whenever a piece gives a
    shorter way to a junction we remember it. After a few rounds nothing improves.
    """
    best = {name: math.inf for name in NODES}  # shortest distance found so far
    best[start] = 0
    came_from = {}
    for _ in NODES:
        for a, b in EDGES:
            if best[a] + length(NODES[a], NODES[b]) < best[b]:
                best[b] = best[a] + length(NODES[a], NODES[b])
                came_from[b] = a

    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    return path[::-1]


def road_start_for(point):
    """The junction at the start of the road piece that this point is on."""
    for a, b in EDGES:
        (x1, y1), (x2, y2) = NODES[a], NODES[b]
        if min(x1, x2) <= point[0] <= max(x1, x2) and min(y1, y2) <= point[1] <= max(y1, y2):
            return a


def direction(a, b):
    """Which way are we going? (1, 0) right, (-1, 0) left, (0, 1) down, (0, -1) up."""
    return ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))


def turn(before, after):
    """'left' or 'right'. y points DOWN on the screen, so a positive cross product is a right turn."""
    return "right" if before[0] * after[1] - before[1] * after[0] > 0 else "left"


def build_route(slot):
    """The route for the website: the points to draw and the directions to read."""
    access = (slot["access_x"], slot["access_y"])  # the spot on the road in front of the bay
    bay = (slot["x"] + slot["width"] / 2, slot["y"] + slot["height"] / 2)
    points = [NODES[name] for name in shortest_path("ENTRY", road_start_for(access))]
    points += [access, bay]

    # distances[i] = how far along the route point i is (the moving dot uses this)
    distances = [0]
    for i in range(1, len(points)):
        distances.append(distances[-1] + length(points[i - 1], points[i]))

    # A "leg" is one straight stretch: [direction, distance where it ends].
    # Pieces that keep going the same way join into one leg.
    legs = []
    for i in range(1, len(points)):
        way = direction(points[i - 1], points[i])
        if legs and legs[-1][0] == way:
            legs[-1][1] = distances[i]
        else:
            legs.append([way, distances[i]])

    steps = []
    for n, (way, end) in enumerate(legs):
        metres = round(end - (legs[n - 1][1] if n else 0))
        if n == 0:
            text = f"Enter through the entry gate and drive straight for {metres} m."
        elif n == len(legs) - 1:
            text = f"Turn {turn(legs[n - 1][0], way)} into bay {slot['label']}. You have arrived."
        else:
            text = f"Turn {turn(legs[n - 1][0], way)} and drive {metres} m."
        steps.append({"text": text, "distance": end})

    return {"points": points, "distances": distances, "steps": steps}
