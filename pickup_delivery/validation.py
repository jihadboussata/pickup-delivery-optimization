"""Check a route from first principles, independently of MILP variables."""

import math

from .instance import Instance


def evaluate_route(instance: Instance, route, tolerance=1e-7):
    route = list(route)
    if len(route) != len(instance.nodes) + 1:
        raise ValueError("A route must visit every customer once and the depot twice.")
    if route[0] != instance.depot or route[-1] != instance.depot:
        raise ValueError("The route must start and end at the depot.")
    if len(set(route[1:-1])) != len(instance.customers) or set(route[1:-1]) != set(instance.customers):
        raise ValueError("Missing, duplicate or unknown customer nodes.")
    positions = {node: k for k, node in enumerate(route[:-1])}
    for r in instance.requests:
        if positions[r.pickup] >= positions[r.delivery]:
            raise ValueError(f"Delivery {r.delivery} precedes pickup {r.pickup}.")
    changes = instance.changes
    loads, load = [0.0], 0.0
    for node in route[1:]:
        load += changes[node]
        if load < -tolerance or load > instance.capacity + tolerance:
            raise ValueError(f"Capacity violation after node {node}: {load}.")
        loads.append(load)
    if not math.isclose(load, 0.0, abs_tol=tolerance):
        raise ValueError("The vehicle must return empty.")
    return {
        "route": route,
        "distance": math.fsum(instance.distance(i, j) for i, j in zip(route, route[1:])),
        "loads": loads,
        "peak_load": max(loads),
        "capacity": instance.capacity,
        "feasible": True,
    }


def reconstruct_route(instance: Instance, selected_arcs):
    """Reject incomplete edge sets and disconnected cycles, rather than looping."""
    arcs = list(selected_arcs)
    if len(arcs) != len(instance.nodes):
        raise ValueError("Expected exactly one selected arc per node.")
    if any(i not in instance.coordinates or j not in instance.coordinates or i == j for i, j in arcs):
        raise ValueError("Invalid selected arc.")
    successor = dict(arcs)
    if set(successor) != set(instance.nodes) or len({j for _, j in arcs}) != len(instance.nodes):
        raise ValueError("Selected arcs must have unit in-degree and out-degree.")
    route, visited = [instance.depot], {instance.depot}
    for _ in instance.customers:
        nxt = successor[route[-1]]
        if nxt in visited:
            raise ValueError("A disconnected subtour or premature depot return was selected.")
        route.append(nxt)
        visited.add(nxt)
    if successor[route[-1]] != instance.depot:
        raise ValueError("The route does not return to the depot.")
    route.append(instance.depot)
    return route
