"""A deterministic heuristic and a small-instance exhaustive reference."""

import itertools
import math

from .instance import Instance
from .validation import evaluate_route


def nearest_feasible(instance: Instance):
    """Choose the nearest admissible customer, breaking distance ties by node ID."""
    remaining, seen = set(instance.customers), set()
    route, load = [instance.depot], 0.0
    delivery_pickup = {r.delivery: r.pickup for r in instance.requests}
    a = instance.changes
    while remaining:
        candidates = [j for j in remaining
                      if delivery_pickup.get(j, instance.depot) in seen | {instance.depot}
                      and -1e-9 <= load + a[j] <= instance.capacity + 1e-9]
        if not candidates:
            raise ValueError("The greedy construction has no admissible next stop.")
        nxt = min(candidates, key=lambda j: (instance.distance(route[-1], j), j))
        route.append(nxt); remaining.remove(nxt); seen.add(nxt); load += a[nxt]
    route.append(instance.depot)
    return evaluate_route(instance, route)


def exhaustive_reference(instance: Instance):
    """Enumerate ALL customer permutations, not the MILP constraints. Up to 8 stops."""
    customers = instance.customers
    if len(customers) > 8:
        raise ValueError("Exhaustive verification is limited to 8 customer nodes (4 requests).")
    best, count = None, 0
    for order in itertools.permutations(customers):
        try:
            checked = evaluate_route(instance, [instance.depot, *order, instance.depot])
        except ValueError:
            continue
        count += 1
        if best is None or checked["distance"] < best["distance"] - 1e-10:
            best = checked
    return {"permutations_checked": math.factorial(len(customers)),
            "feasible_routes": count, "best": best}
