"""Load a small, explicit JSON schema; never infer requests from node numbers."""

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Request:
    pickup: int
    delivery: int
    quantity: float


@dataclass(frozen=True)
class Instance:
    name: str
    coordinates: dict[int, tuple[float, float]]
    requests: tuple[Request, ...]
    capacity: float
    depot: int = 0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("The instance needs a non-empty name.")
        if not self.coordinates or any(type(i) is not int for i in self.coordinates):
            raise ValueError("Node IDs must be unique integers.")
        if type(self.depot) is not int or self.depot not in self.coordinates:
            raise ValueError("The depot must be a declared node.")
        if not math.isfinite(self.capacity) or self.capacity <= 0:
            raise ValueError("Capacity must be finite and positive.")
        for xy in self.coordinates.values():
            if len(xy) != 2 or not all(math.isfinite(v) for v in xy):
                raise ValueError("Each node needs two finite coordinates.")
        if not self.requests:
            raise ValueError("At least one request is required.")
        endpoints = []
        for r in self.requests:
            if type(r.pickup) is not int or type(r.delivery) is not int:
                raise ValueError("Request endpoints must be integer IDs.")
            if not math.isfinite(r.quantity) or r.quantity <= 0:
                raise ValueError("Request quantities must be finite and positive.")
            if r.pickup == r.delivery or self.depot in (r.pickup, r.delivery):
                raise ValueError("Pickup, delivery and depot must be distinct.")
            endpoints.extend((r.pickup, r.delivery))
        if len(endpoints) != len(set(endpoints)):
            raise ValueError("Each customer node must belong to exactly one request.")
        if set(endpoints) != set(self.coordinates) - {self.depot}:
            raise ValueError("Requests must cover exactly the non-depot nodes.")

    @property
    def nodes(self):
        return tuple(sorted(self.coordinates))

    @property
    def customers(self):
        return tuple(i for i in self.nodes if i != self.depot)

    @property
    def changes(self):
        a = {i: 0.0 for i in self.nodes}
        for r in self.requests:
            a[r.pickup], a[r.delivery] = r.quantity, -r.quantity
        return a

    def distance(self, i, j):
        return math.dist(self.coordinates[i], self.coordinates[j])

    def with_capacity(self, capacity):
        return replace(self, capacity=float(capacity))


def load_instance(path: str | Path) -> Instance:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data["nodes"]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate node IDs in JSON.")
    return Instance(
        name=data["name"],
        coordinates={r["id"]: (float(r["x"]), float(r["y"])) for r in rows},
        requests=tuple(Request(r["pickup"], r["delivery"], float(r["quantity"]))
                       for r in data["requests"]),
        capacity=float(data["capacity"]),
        depot=data.get("depot", 0),
    )
