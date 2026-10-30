# From assessed coursework to a portfolio project

The supplied notebook and report remain the source of the problem, numerical instance and original Gurobi formulation. This repository is a documented redevelopment, not a claim to invent the routing model or create an industrial deployment.

## Preserved

- One vehicle, one depot, four pickup-delivery requests, capacity 5 and Euclidean distances.
- The actual request list `(1,8,2), (2,6,3), (3,7,2), (4,5,1)`.
- MILP arc, order and post-service load variables; MTZ and precedence logic.
- Original result: route `0-4-1-5-2-6-3-7-8-0`, objective 39.1757429352.

## Changed

1. Replaced notebook-only globals with reusable modules, validated JSON input, a command-line interface and an installable package.
2. Retained Gurobi as an optional backend and added HiGHS through SciPy as the license-free default. Both use the same sparse formulation.
3. Removed the duplicated depot-order equality, the unused depot-order variable and explicit bound rows represented directly by variable bounds.
4. Tightened MTZ's constant from the total node count to the number of customer stops; derived separate load constants from capacity and the target node's load change.
5. Replaced the source notebook's misleading node comments (e.g. node 5 labelled delivery 1) with request-derived P1/D1 labels. Node 5 actually delivers request 4; node 8 delivers request 1.
6. Added guarded route reconstruction and independent checks for all visits, pair precedence, capacity, empty return and objective consistency.
7. Preserved distinct solver outcomes: optimal, feasible at a limit, infeasible, no incumbent and solver error. An interrupted run is not labelled optimal.
8. Added nearest-feasible routing as an explicit reproducible baseline. Did not present the original solver's intermediate incumbents as independently designed baselines.
9. Verified the solution by enumerating every customer permutation. Added a capacity sensitivity experiment and checked each case independently.
10. Rebuilt plots with directed route arrows, correct pair labels and a post-service load trajectory. Added machine-readable results, dependency versions and data hashes.
11. Added tests for wrong precedence despite nonnegative aggregate load, overcapacity, subtours, invalid data, arbitrary node IDs and solver time limits. Standard CI needs no Gurobi license.
12. Replaced grading-oriented notebook/report prose with an executed project walkthrough, concise README, formulation, limitations, attribution and scoped licensing.

## Validation record

The local 2026-10-30 run used Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0 and Matplotlib 3.10.8. All 12 tests passed with Gurobi 13.0.1 installed, including agreement between HiGHS, Gurobi and exhaustive enumeration. Standard CI intentionally skips the optional Gurobi test when the package is absent. Committed results are from HiGHS; the optional solver's check is summarized in [backend_verification.json](../results/backend_verification.json).
