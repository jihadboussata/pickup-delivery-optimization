# Mathematical formulation

## Data and assumptions

Let $V = \{0\} \cup C$ be the nodes, where $0$ denotes the depot (the implementation also accepts other integer depot IDs), $C$ contains $m$ customer stops, and $A = \{(i,j): i,j \in V, i \ne j\}$. Request $r$ has a distinct pickup $p_r$, delivery $d_r$ and quantity $q_r > 0$. Every customer belongs to one request. Capacity is $Q > 0$, and the Euclidean cost is $c_{ij}$. A request with $q_r > Q$ immediately makes the instance infeasible.

Define $a_0=0$, $a_{p_r}=q_r$ and $a_{d_r}=-q_r$. The JSON request pairs are authoritative: **1 delivers to 8, 2 to 6, 3 to 7, and 4 to 5**. Node numbering does not encode pair membership.

## Variables and objective

- $x_{ij} \in \{0,1\}$: arc selected.
- $1 \le u_i \le m$ for $i \in C$: continuous visit-order variables.
- $0 \le L_i \le Q$ for $i \in V$: load **after** service; $L_0=0$ fixed by bounds.

Minimize

$$\sum_{(i,j)\in A}c_{ij}x_{ij}.$$

## Degree, order and precedence

$$\sum_{j\ne i}x_{ij}=1\quad(i\in V), \qquad
\sum_{i\ne j}x_{ij}=1\quad(j\in V).$$

Degree constraints alone permit disconnected cycles. For distinct $i,j\in C$, impose

$$u_i-u_j+m x_{ij}\le m-1.$$

When an arc is selected, $u_j\ge u_i+1$. Summing around any customer-only cycle gives a contradiction. The depot is excluded to permit the return arc. Together with unit degrees, this leaves one tour through all nodes. The bounds $1\le u_i\le m$ are sufficient; there is no unused depot order variable. On a full customer chain they force successive order values 1 through $m$ even though the variables are continuous.

For each request:

$$u_{p_r}+1\le u_{d_r}.$$

This is needed in addition to nonnegative total load: carrying another request's goods must not allow a delivery before its own pickup.

## Load propagation with derived big-M constants

For every arc, including those incident to the depot:

$$L_j\ge L_i+a_j-(Q+a_j)(1-x_{ij}),$$

$$L_j\le L_i+a_j+(Q-a_j)(1-x_{ij}).$$

For a potentially feasible instance, $|a_j|\le Q$, so both constants are nonnegative. With $x_{ij}=1$, these inequalities impose $L_j=L_i+a_j$. With $x_{ij}=0$, they become $-Q\le L_j-L_i\le Q$, already implied by the load bounds. Thus neither inequality cuts off an unused arc's admissible load values. A single larger constant $Q+\max q_r$ is valid but more conservative.

On the return arc $i\to0$, the equality imposes $0=L_i$, so the truck returns empty. For balanced, fully served requests this agrees with direct cumulative-load accounting.

## What the optimum means

The reported objective is distance in the example's coordinate units. Solver `optimal` means optimal within numerical tolerances; a requested relative MIP gap of zero is not exact real arithmetic. For this four-request instance, a separate enumeration of all $8!$ orders confirms the objective independently of the MILP formulation. It finds 864 feasible routes and the same minimizing sequence.

The model has $|A|+m+|V|=89$ variables and $2|V|+m(m-1)+|R|+2|A|=222$ constraints, excluding bounds. Removing an unused depot order variable and redundant bound rows explains the count difference from the coursework notebook.
