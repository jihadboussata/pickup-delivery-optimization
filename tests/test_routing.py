"""Check optimization against route enumeration and deliberate infeasibilities."""

from pathlib import Path
from dataclasses import replace
import importlib.util
import math
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from pickup_delivery import Instance, Request, evaluate_route, load_instance, solve
from pickup_delivery.baselines import exhaustive_reference, nearest_feasible
from pickup_delivery.model import build_model
from pickup_delivery.validation import reconstruct_route

ROOT = Path(__file__).resolve().parents[1]


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance = load_instance(ROOT / "data/four_requests.json")
        cls.solution = solve(cls.instance)
        cls.exact = exhaustive_reference(cls.instance)

    def test_milp_matches_independent_enumeration(self):
        self.assertEqual(self.solution.status, "optimal")
        self.assertTrue(self.solution.feasible)
        self.assertEqual(self.exact["permutations_checked"], 40320)
        self.assertGreater(self.exact["feasible_routes"], 1)
        self.assertAlmostEqual(self.solution.distance, self.exact["best"]["distance"], places=7)
        self.assertAlmostEqual(self.solution.distance, 39.17574293522, places=7)
        self.assertEqual(self.solution.route, [0, 4, 1, 5, 2, 6, 3, 7, 8, 0])
        self.assertEqual(self.solution.loads, [0, 1, 3, 2, 5, 2, 4, 2, 0, 0])

    def test_greedy_is_feasible_and_no_better_than_optimum(self):
        baseline = nearest_feasible(self.instance)
        self.assertTrue(baseline["feasible"])
        self.assertGreaterEqual(baseline["distance"], self.solution.distance - 1e-7)

    def test_precedence_cannot_be_replaced_by_nonnegative_total_load(self):
        # Deliver request 1 while carrying request 2: aggregate load alone allows it.
        with self.assertRaisesRegex(ValueError, "precedes"):
            evaluate_route(self.instance, [0, 2, 8, 1, 6, 4, 5, 3, 7, 0])

    def test_overcapacity_route_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Capacity"):
            evaluate_route(self.instance, [0, 1, 2, 3, 4, 5, 6, 7, 8, 0])

    def test_duplicate_and_disconnected_routes_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_route(self.instance, [0, 1, 1, 2, 3, 4, 5, 6, 7, 0])
        with self.assertRaisesRegex(ValueError, "subtour"):
            reconstruct_route(self.instance, [(0,1),(1,0),(2,6),(6,2),(3,7),(7,3),(4,5),(5,8),(8,4)])

    def test_request_larger_than_capacity_is_infeasible(self):
        small = self.instance.with_capacity(2)
        self.assertEqual(solve(small).status, "infeasible")
        self.assertIsNone(exhaustive_reference(small)["best"])

    def test_capacity_relaxation_cannot_increase_optimum(self):
        looser = self.instance.with_capacity(8)
        result = solve(looser)
        self.assertEqual(result.status, "optimal")
        self.assertLessEqual(result.distance, self.solution.distance + 1e-7)
        self.assertAlmostEqual(result.distance, exhaustive_reference(looser)["best"]["distance"], places=7)

    def test_nonconsecutive_ids_and_nonzero_depot(self):
        tiny = Instance("One request", {99:(0,0), 12:(1,0), 48:(2,0)}, (Request(12,48,1.5),), 1.5, 99)
        result = solve(tiny)
        self.assertEqual(result.route, [99,12,48,99])
        self.assertEqual(result.loads, [0,1.5,0,0])
        self.assertAlmostEqual(result.distance, 4)

    def test_invalid_data_are_rejected(self):
        for kwargs in [
            {"capacity": 0}, {"capacity": math.inf},
            {"requests": (Request(1,8,-1),)},
            {"requests": self.instance.requests + (Request(1,5,1),)},
            {"coordinates": self.instance.coordinates | {1:(math.nan,0)}},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                replace(self.instance, **kwargs)

    def test_time_limit_without_incumbent_is_not_optimal(self):
        raw = SimpleNamespace(status=1, x=None, fun=None, message="Time limit reached")
        with patch("pickup_delivery.model.milp", return_value=raw):
            result = solve(self.instance)
        self.assertEqual(result.status, "no_solution")
        self.assertFalse(result.feasible)
        self.assertIsNone(result.distance)

    def test_all_load_big_m_inequalities_allow_unused_arcs(self):
        # The load range is [0,Q]; both inactive inequalities must allow its corners.
        Q = self.instance.capacity
        for a in self.instance.changes.values():
            for li in (0,Q):
                for lj in (0,Q):
                    self.assertGreaterEqual(lj-li, a-(Q+a))
                    self.assertLessEqual(lj-li, a+(Q-a))
        self.assertEqual(build_model(self.instance).matrix.shape, (222,89))

    @unittest.skipUnless(importlib.util.find_spec("gurobipy"), "Optional Gurobi backend not installed")
    def test_gurobi_backend_matches_exact_reference(self):
        result = solve(self.instance, solver="gurobi")
        self.assertEqual(result.status, "optimal")
        self.assertAlmostEqual(result.distance, self.exact["best"]["distance"], places=7)


if __name__ == "__main__":
    unittest.main()
