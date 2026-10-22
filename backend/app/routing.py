"""Finds the route from the entry gate to a slot and writes the directions.

1. The roads are a small graph: junctions (NODES) joined by one-way pieces (EDGES).
2. We find the shortest way from ENTRY to the road piece in front of the slot.
   One-way pieces mean we can never drive the wrong way.
3. The last bit goes from the road straight into the bay.
4. We turn the points into sentences: "Turn right and drive 33 m".
"""
import math

from .layout import EDGES, NODES


def length(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def shortest_path(start, goal):
    """The shortest way along the one-way roads, as a list of junction names.

    We go over all the road pieces again and again, and whenever a piece gives a
    shorter way to a junction we remember it. After a few rounds nothing improves.
    """
    best = {name: math.inf for name in NODES}  # shortest distance found so far
    best[start] = 0
    came_from = {}
    for _ in NODES:
        for a, b in EDGES:
            distance = best[a] + length(NODES[a], NODES[b])
            if distance < best[b]:
                best[b] = distance
                came_from[b] = a

    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    return path[::-1]


def road_start_for(point):
    """The junction at the start of the road piece that this point is on."""
    x, y = point
    for a, b in EDGES:
        (x1, y1), (x2, y2) = NODES[a], NODES[b]
        if min(x1, x2) - 0.01 <= x <= max(x1, x2) + 0.01 and min(y1, y2) - 0.01 <= y <= max(y1, y2) + 0.01:
            return a
    raise ValueError("The slot is not next to a road")


def direction(a, b):
    """Which way are we going? (1, 0) right, (-1, 0) left, (0, 1) down, (0, -1) up."""
    return ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))


def turn(before, after):
    """'left' or 'right'. On the screen y points DOWN, so a positive cross product is a right turn."""
    return "right" if before[0] * after[1] - before[1] * after[0] > 0 else "left"


def build_route(slot):
    """The route for the frontend: the points to draw and the directions to read."""
    access = (slot["access_x"], slot["access_y"])  # the spot on the road in front of the bay
    bay = (slot["x"] + slot["width"] / 2, slot["y"] + slot["height"] / 2)
    points = [NODES[name] for name in shortest_path("ENTRY", road_start_for(access))]
    points += [access, bay]

    # distances[i] = how far along the route point i is (the moving dot uses this)
    distances = [0.0]
    for i in range(1, len(points)):
        distances.append(distances[-1] + length(points[i - 1], points[i]))

    # A "leg" is one straight stretch. Pieces that keep the same direction join into one leg.
    legs = []  # each leg: [direction, first point, last point]
    for i in range(1, len(points)):
        way = direction(points[i - 1], points[i])
        if legs and legs[-1][0] == way:
            legs[-1][2] = i
        else:
            legs.append([way, i - 1, i])

    steps = []
    for n, (way, first, last) in enumerate(legs):
        metres = round(distances[last] - distances[first])
        if n == 0:
            text = f"Enter through the entry gate and drive straight for {metres} m."
        elif n == len(legs) - 1:
            text = f"Turn {turn(legs[n - 1][0], way)} into bay {slot['label']}. You have arrived."
        else:
            text = f"Turn {turn(legs[n - 1][0], way)} and drive {metres} m."
        steps.append({"text": text, "distance": round(distances[last], 2)})

    return {
        "points": points,
        "distances": [round(d, 2) for d in distances],
        "length_m": round(distances[-1]),
        "steps": steps,
    }
