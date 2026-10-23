"""Build a route from the entry gate to a particular parking bay."""

import math

from .layout import EDGES, NODES


def distance_between(point_a, point_b):
    """Straight-line distance between two map points."""
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return math.hypot(dx, dy)


def shortest_path(start, goal):
    """Find the shortest directed road path using repeated distance updates.

    This small version of the Bellman-Ford method is easy to follow:
    repeatedly check every road and remember any shorter way to its end.
    """
    best_distance = {name: math.inf for name in NODES}
    best_distance[start] = 0
    previous_junction = {}

    # With N junctions, a shortest route cannot need more than N-1 road edges.
    for _ in range(len(NODES)):
        for road_start, road_end in EDGES:
            road_length = distance_between(
                NODES[road_start], NODES[road_end]
            )
            new_distance = best_distance[road_start] + road_length
            if new_distance < best_distance[road_end]:
                best_distance[road_end] = new_distance
                previous_junction[road_end] = road_start

    # Walk backward from the destination to rebuild the route.
    path = [goal]
    while path[-1] != start:
        path.append(previous_junction[path[-1]])
    path.reverse()
    return path


def road_start_for(point):
    """Find the first junction of the road segment containing a point."""
    x, y = point
    for road_start, road_end in EDGES:
        start_x, start_y = NODES[road_start]
        end_x, end_y = NODES[road_end]

        on_segment_x = min(start_x, end_x) - 0.01 <= x <= max(start_x, end_x) + 0.01
        on_segment_y = min(start_y, end_y) - 0.01 <= y <= max(start_y, end_y) + 0.01
        if on_segment_x and on_segment_y:
            return road_start

    raise ValueError("The slot is not next to a road")


def direction(point_a, point_b):
    """Return the horizontal and vertical direction of a straight segment."""
    dx = (point_b[0] > point_a[0]) - (point_b[0] < point_a[0])
    dy = (point_b[1] > point_a[1]) - (point_b[1] < point_a[1])
    return (dx, dy)


def turn_direction(previous_direction, next_direction):
    """Say whether the route turns left or right on the screen."""
    cross_product = (
        previous_direction[0] * next_direction[1]
        - previous_direction[1] * next_direction[0]
    )
    return "right" if cross_product > 0 else "left"


def build_route(slot):
    """Return route points, travelled distances, total length, and directions."""
    access_point = (slot["access_x"], slot["access_y"])
    bay_center = (
        slot["x"] + slot["width"] / 2,
        slot["y"] + slot["height"] / 2,
    )

    junction_names = shortest_path("ENTRY", road_start_for(access_point))
    points = [NODES[name] for name in junction_names]
    points.extend([access_point, bay_center])

    # Store how far along the route each point is, starting at zero metres.
    distances = [0.0]
    for index in range(1, len(points)):
        segment_length = distance_between(points[index - 1], points[index])
        distances.append(distances[-1] + segment_length)

    # Join consecutive segments that point in the same direction.
    legs = []
    for index in range(1, len(points)):
        travel_direction = direction(points[index - 1], points[index])
        if legs and legs[-1][0] == travel_direction:
            legs[-1][2] = index
        else:
            legs.append([travel_direction, index - 1, index])

    # Turn each leg into a short instruction for the driver.
    steps = []
    for leg_number, (travel_direction, first_point, last_point) in enumerate(legs):
        leg_length = round(distances[last_point] - distances[first_point])

        if leg_number == 0:
            text = f"Enter through the entry gate and drive straight for {leg_length} m."
        elif leg_number == len(legs) - 1:
            turn = turn_direction(legs[leg_number - 1][0], travel_direction)
            text = f"Turn {turn} into bay {slot['label']}. You have arrived."
        else:
            turn = turn_direction(legs[leg_number - 1][0], travel_direction)
            text = f"Turn {turn} and drive {leg_length} m."

        steps.append({"text": text, "distance": round(distances[last_point], 2)})

    return {
        "points": points,
        "distances": [round(value, 2) for value in distances],
        "length_m": round(distances[-1]),
        "steps": steps,
    }
