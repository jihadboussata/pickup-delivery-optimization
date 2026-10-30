"""Run a documented experiment and export auditable results."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

import matplotlib
import numpy
import scipy

from .baselines import exhaustive_reference, nearest_feasible
from .instance import load_instance
from .model import solve
from .plots import plot_capacity, plot_solution


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, default=Path("data/four_requests.json"))
    parser.add_argument("--solver", choices=("highs", "gurobi"), default="highs")
    parser.add_argument("--capacity", type=float)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--verify", action="store_true", help="Enumerate every order, up to 8 customer stops.")
    parser.add_argument("--sensitivity", nargs="+", type=float, metavar="Q")
    parser.add_argument("--output", type=Path, default=Path("results-local"))
    args = parser.parse_args(argv)
    try:
        instance = load_instance(args.instance)
        if args.capacity is not None: instance = instance.with_capacity(args.capacity)
        solution = solve(instance, args.solver, args.time_limit)
        args.output.mkdir(parents=True, exist_ok=True)
        write_json(args.output / "solution.json", solution.to_dict())
        print(f"Status: {solution.status}")
        if not solution.feasible:
            print(solution.message)
            return 2
        print("Route:", " -> ".join(map(str, solution.route)))
        print(f"Distance: {solution.distance:.10f}")
        comparison = {"nearest_feasible": nearest_feasible(instance)}
        comparison["distance_reduction_vs_greedy_percent"] = 100 * (1 - solution.distance / comparison["nearest_feasible"]["distance"])
        if args.verify:
            exact = exhaustive_reference(instance)
            comparison["exhaustive"] = exact
            if exact["best"] is None or not math.isclose(solution.distance, exact["best"]["distance"], abs_tol=1e-6):
                raise RuntimeError("MILP does not match the independent exhaustive optimum.")
            comparison["matches_exhaustive_optimum"] = True
        write_json(args.output / "comparison.json", comparison)
        with (args.output / "route.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["visit", "node", "load_after_service", "distance_from_previous"])
            for k, (node, load) in enumerate(zip(solution.route, solution.loads)):
                writer.writerow([k, node, load, 0.0 if k == 0 else instance.distance(solution.route[k-1], node)])
        plot_solution(instance, solution, args.output / "route_and_load.png")
        if args.sensitivity:
            rows = []
            for capacity in sorted(set(args.sensitivity)):
                varied = instance.with_capacity(capacity)
                result = solve(varied, args.solver, args.time_limit)
                row = {"capacity": capacity, "status": result.status, "distance": result.distance,
                       "peak_load": result.peak_load, "verified_exhaustively": False}
                if args.verify:
                    exact = exhaustive_reference(varied)
                    if exact["best"] is None:
                        if result.status != "infeasible": raise RuntimeError("Infeasibility mismatch.")
                    elif not result.feasible or not math.isclose(result.distance, exact["best"]["distance"], abs_tol=1e-6):
                        raise RuntimeError("Sensitivity experiment disagrees with exhaustive verification.")
                    row["verified_exhaustively"] = True
                rows.append(row)
            with (args.output / "capacity_sensitivity.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            plot_capacity(rows, args.output / "capacity_sensitivity.png")
        environment = {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__,
                       "matplotlib": matplotlib.__version__, "solver": args.solver,
                       "instance_sha256": hashlib.sha256(args.instance.read_bytes()).hexdigest(),
                       "effective_capacity": instance.capacity,
                       "command_arguments": vars(args) | {"instance": str(args.instance), "output": str(args.output)}}
        if args.solver == "gurobi":
            import gurobipy
            environment["gurobi"] = ".".join(map(str, gurobipy.gurobi.version()))
        write_json(args.output / "environment.json", environment)
        return 0 if solution.status == "optimal" else 3
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
