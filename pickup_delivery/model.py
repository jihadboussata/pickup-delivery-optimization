"""One MILP formulation, with HiGHS and optional Gurobi backends."""

from dataclasses import asdict, dataclass
import math

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from .instance import Instance
from .validation import evaluate_route, reconstruct_route


@dataclass
class Formulation:
    objective: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    integrality: np.ndarray
    matrix: object
    row_lower: np.ndarray
    row_upper: np.ndarray
    arcs: tuple
    arc_index: dict


@dataclass
class Solution:
    solver: str
    status: str
    message: str
    route: list | None = None
    distance: float | None = None
    loads: list | None = None
    peak_load: float | None = None
    capacity: float | None = None
    feasible: bool = False
    dual_bound: float | None = None
    relative_gap: float | None = None
    variables: int | None = None
    constraints: int | None = None

    def to_dict(self):
        return asdict(self)


def build_model(instance: Instance) -> Formulation:
    """x = binary arcs; u = continuous customer order; L = post-service load."""
    nodes, customers = instance.nodes, instance.customers
    arcs = tuple((i, j) for i in nodes for j in nodes if i != j)
    x = {arc: k for k, arc in enumerate(arcs)}
    u = {i: len(x) + k for k, i in enumerate(customers)}
    load = {i: len(x) + len(u) + k for k, i in enumerate(nodes)}
    size, m, Q = len(x) + len(u) + len(load), len(customers), instance.capacity
    objective = np.zeros(size)
    lower, upper = np.zeros(size), np.zeros(size)
    integer = np.zeros(size, dtype=int)
    for (i, j), k in x.items():
        objective[k], upper[k], integer[k] = instance.distance(i, j), 1, 1
    for k in u.values():
        lower[k], upper[k] = 1, m
    for k in load.values():
        upper[k] = Q
    upper[load[instance.depot]] = 0
    row_ids, col_ids, values, row_lower, row_upper = [], [], [], [], []

    def add(coefficients, lb=-np.inf, ub=np.inf):
        row = len(row_lower)
        for col, value in coefficients.items():
            if value:
                row_ids.append(row); col_ids.append(col); values.append(value)
        row_lower.append(lb); row_upper.append(ub)

    for i in nodes:
        add({x[i, j]: 1 for j in nodes if j != i}, 1, 1)
        add({x[j, i]: 1 for j in nodes if j != i}, 1, 1)
    for i in customers:
        for j in customers:
            if i != j:
                add({u[i]: 1, u[j]: -1, x[i, j]: m}, ub=m - 1)
    for r in instance.requests:
        add({u[r.pickup]: 1, u[r.delivery]: -1}, ub=-1)
    a = instance.changes
    for i, j in arcs:
        # Separate valid constants for the lower and upper load inequalities.
        m_lower, m_upper = Q + a[j], Q - a[j]
        add({load[j]: 1, load[i]: -1, x[i, j]: -m_lower}, lb=-Q)
        add({load[j]: 1, load[i]: -1, x[i, j]: m_upper}, ub=Q)
    matrix = coo_matrix((values, (row_ids, col_ids)), shape=(len(row_lower), size)).tocsc()
    return Formulation(objective, lower, upper, integer, matrix,
                       np.array(row_lower), np.array(row_upper), arcs, x)


def _finite(value):
    return float(value) if value is not None and math.isfinite(value) else None


def solve(instance: Instance, solver="highs", time_limit=60.0) -> Solution:
    if solver not in ("highs", "gurobi"):
        raise ValueError("Choose solver='highs' or solver='gurobi'.")
    if not math.isfinite(time_limit) or time_limit <= 0:
        raise ValueError("Time limit must be finite and positive.")
    if any(r.quantity > instance.capacity for r in instance.requests):
        return Solution(solver, "infeasible", "A request exceeds vehicle capacity.", capacity=instance.capacity)
    f = build_model(instance)
    if solver == "highs":
        raw = milp(f.objective, integrality=f.integrality,
                   bounds=Bounds(f.lower, f.upper),
                   constraints=LinearConstraint(f.matrix, f.row_lower, f.row_upper),
                   options={"mip_rel_gap": 0.0, "time_limit": time_limit})
        vector, obj = raw.x, raw.fun
        status = {0: "optimal", 1: "feasible_limit" if vector is not None else "no_solution",
                  2: "infeasible", 3: "unbounded", 4: "solver_error"}.get(raw.status, "solver_error")
        message, bound, gap = raw.message, getattr(raw, "mip_dual_bound", None), getattr(raw, "mip_gap", None)
    else:
        try:
            import gurobipy as gp
        except ImportError as exc:
            raise RuntimeError("Install the optional 'gurobi' extra; HiGHS needs no Gurobi license.") from exc
        try:
            with gp.Env(empty=True) as env:
                env.setParam("OutputFlag", 0); env.start()
                with gp.Model("pickup_delivery", env=env) as model:
                    model.Params.TimeLimit = time_limit
                    model.Params.MIPGap = 0.0
                    model.Params.Threads = 1
                    variables = [model.addVar(lb=float(f.lower[k]), ub=float(f.upper[k]),
                                 vtype=gp.GRB.BINARY if f.integrality[k] else gp.GRB.CONTINUOUS)
                                 for k in range(len(f.objective))]
                    model.setObjective(gp.LinExpr(f.objective.tolist(), variables), gp.GRB.MINIMIZE)
                    rows = f.matrix.tocsr()
                    for k in range(rows.shape[0]):
                        start, stop = rows.indptr[k:k + 2]
                        expression = gp.LinExpr(rows.data[start:stop].tolist(),
                                               [variables[j] for j in rows.indices[start:stop]])
                        lb, ub = f.row_lower[k], f.row_upper[k]
                        if lb == ub:
                            model.addConstr(expression == float(lb))
                        else:
                            if np.isfinite(lb): model.addConstr(expression >= float(lb))
                            if np.isfinite(ub): model.addConstr(expression <= float(ub))
                    model.optimize()
                    vector = np.array([v.X for v in variables]) if model.SolCount else None
                    obj = model.ObjVal if model.SolCount else None
                    status = ("optimal" if model.Status == gp.GRB.OPTIMAL else
                              "infeasible" if model.Status == gp.GRB.INFEASIBLE else
                              "feasible_limit" if vector is not None else "no_solution")
                    message = f"Gurobi status code {model.Status}"
                    bound = model.ObjBound if model.Status in (gp.GRB.OPTIMAL, gp.GRB.TIME_LIMIT) else None
                    gap = model.MIPGap if model.SolCount else None
        except gp.GurobiError as exc:
            raise RuntimeError("Gurobi could not run. Check its installation/license or use --solver highs.") from exc
    solution = Solution(solver, status, message, capacity=instance.capacity,
                        dual_bound=_finite(bound), relative_gap=_finite(gap),
                        variables=len(f.objective), constraints=f.matrix.shape[0])
    if vector is not None and status in ("optimal", "feasible_limit"):
        selected = [arc for arc in f.arcs if vector[f.arc_index[arc]] > 0.5]
        verified = evaluate_route(instance, reconstruct_route(instance, selected))
        if not math.isclose(verified["distance"], obj, rel_tol=1e-7, abs_tol=1e-6):
            raise RuntimeError("Solver objective disagrees with the independently computed route distance.")
        for key, value in verified.items():
            setattr(solution, key, value)
    return solution
