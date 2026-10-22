"""Finds the exact route from the entry gate to a slot, and writes the directions.

How it works:
1. The roads are a small graph: junctions (NODES) joined by one-way pieces (EDGES).
2. Dijkstra's algorithm finds the shortest way from ENTRY to the road piece in
   front of the slot. One-way pieces mean we can never drive the wrong way.
3. The last bit goes from the road straight into the bay.
4. We turn the list of points into sentences: "turn left", "drive 24 m", ...
"""
import heapq
import math

from .layout import EDGES, NODES


def distance(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def shortest_path(start, goal):
    """Dijkstra: the list of junction names to follow from start to goal."""
    best = {start: 0}
    came_from = {}
    queue = [(0, start)]
    while queue:
        so_far, node = heapq.heappop(queue)
        if node == goal:
            break
        if so_far > best.get(node, float("inf")):
            continue
        for a, b in EDGES:
            if a == node:
                total = so_far + distance(NODES[a], NODES[b])
                if total < best.get(b, float("inf")):
                    best[b] = total
                    came_from[b] = a
                    heapq.heappush(queue, (total, b))
    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    return path[::-1]


def edge_containing(point):
    """Which one-way road piece is this point on? Returns (from_junction, to_junction)."""
    px, py = point
    for a, b in EDGES:
        (x1, y1), (x2, y2) = NODES[a], NODES[b]
        on_line = abs(px - x1) < 0.01 if x1 == x2 else abs(py - y1) < 0.01
        within = min(x1, x2) - 0.01 <= px <= max(x1, x2) + 0.01 and \
            min(y1, y2) - 0.01 <= py <= max(y1, y2) + 0.01
        if on_line and within:
            return a, b
    raise ValueError("The slot is not next to a road")


def route_points(slot):
    """The points to drive through: gate, junctions, the spot on the road, the bay."""
    access = (slot["access_x"], slot["access_y"])
    bay_centre = (slot["x"] + slot["width"] / 2, slot["y"] + slot["height"] / 2)
    road_start, _ = edge_containing(access)

    points = [NODES[n] for n in shortest_path("ENTRY", road_start)]
    for p in (access, bay_centre):
        if distance(points[-1], p) > 0.01:
            points.append(p)
    return remove_straight_points(points)


def remove_straight_points(points):
    """Drop points where the route keeps going straight, so "straight" is one step."""
    kept = [points[0]]
    for i in range(1, len(points) - 1):
        before = heading(kept[-1], points[i])
        after = heading(points[i], points[i + 1])
        if abs(before[0] * after[1] - before[1] * after[0]) > 0.01:  # it turns here
            kept.append(points[i])
    kept.append(points[-1])
    return kept


def heading(a, b):
    length = distance(a, b)
    return ((b[0] - a[0]) / length, (b[1] - a[1]) / length)


def turn_word(h1, h2):
    """Left or right? On the screen y points DOWN, so a positive cross product is a right turn."""
    cross = h1[0] * h2[1] - h1[1] * h2[0]
    return "right" if cross > 0 else "left"


def build_route(slot):
    """The full answer for the frontend: points, total length and step-by-step text."""
    points = route_points(slot)

    # Cumulative distance along the route at every point (the dot uses this to move)
    along = [0.0]
    for i in range(1, len(points)):
        along.append(along[-1] + distance(points[i - 1], points[i]))

    steps = []
    for i in range(1, len(points)):
        length = round(distance(points[i - 1], points[i]))
        h = heading(points[i - 1], points[i])
        is_last = i == len(points) - 1

        if i == 1:
            text = f"Enter through the entry gate and drive straight for {length} m."
            if is_last:
                text = "Enter through the entry gate."
        else:
            previous = heading(points[i - 2], points[i - 1])
            side = turn_word(previous, h)
            if is_last:
                text = (f"Turn {side} into bay {slot['label']} ({slot['row_name']}). "
                        f"You have arrived.")
            else:
                text = f"Turn {side} and drive {length} m."

        # the last drive along the road ends in front of the bay: say which side it is on
        if i == len(points) - 2 and len(points) > 2:
            into_bay = heading(points[i], points[i + 1])
            text = text.rstrip(".") + f", then bay {slot['label']} is on your {turn_word(h, into_bay)}."

        steps.append({"text": text, "point_index": i, "distance": along[i]})

    return {
        "slot": {"id": slot["id"], "label": slot["label"], "row_name": slot["row_name"],
                 "size_class": slot["size_class"]},
        "points": [{"x": round(x, 2), "y": round(y, 2)} for x, y in points],
        "distances": [round(d, 2) for d in along],
        "length_m": round(along[-1]),
        "steps": steps,
    }
