"""Headless figures showing the route, load trajectory and capacity experiment."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def plot_solution(instance, solution, path):
    fig, (ax, load_ax) = plt.subplots(1, 2, figsize=(12, 5.1), gridspec_kw={"width_ratios": [1.2, 1]})
    fig.patch.set_facecolor("#fafcfe")
    route = solution.route
    pickup = {r.pickup for r in instance.requests}
    roles = {r.pickup: f"P{k}" for k, r in enumerate(instance.requests, 1)}
    roles.update({r.delivery: f"D{k}" for k, r in enumerate(instance.requests, 1)})
    roles[instance.depot] = "Depot"
    for k, (i, j) in enumerate(zip(route, route[1:]), 1):
        xi, yi = instance.coordinates[i]; xj, yj = instance.coordinates[j]
        ax.annotate("", xy=(xj, yj), xytext=(xi, yi),
                    arrowprops={"arrowstyle": "->", "color": "#607c92", "lw": 1.5, "shrinkA": 8, "shrinkB": 8}, zorder=1)
    for node, (x, y) in instance.coordinates.items():
        marker, color = ("s", "#20384f") if node == instance.depot else (("^", "#178b88") if node in pickup else ("o", "#d38138"))
        ax.scatter(x, y, c=color, marker=marker, s=85, zorder=3)
        ax.annotate(f"{node} · {roles[node]}", (x, y), xytext=(8, 9), textcoords="offset points", fontsize=8.5, color="#20384f")
    ax.set(xlabel="x (coordinate units)", ylabel="y (coordinate units)", xlim=(-1, 12), ylim=(-1, 11.2))
    ax.set_aspect("equal"); ax.grid(alpha=.14)
    ax.set_title("Optimal visit sequence", loc="left", fontweight="bold", color="#20384f", pad=14)
    ax.legend(handles=[Line2D([], [], marker=m, color="none", markerfacecolor=c, markeredgecolor=c, label=l)
                       for m,c,l in [("s","#20384f","Depot"),("^","#178b88","Pickup"),("o","#d38138","Delivery")]],
              loc="lower right", frameon=False, fontsize=8)
    loads = solution.loads
    steps = list(range(len(route)))
    load_ax.step(steps, loads, where="post", lw=2.3, color="#178b88")
    load_ax.scatter(steps, loads, color="#178b88", s=28, zorder=3)
    load_ax.axhline(instance.capacity, color="#d38138", ls="--", lw=1.2, label=f"Capacity = {instance.capacity:g}")
    load_ax.set_xticks(steps, [str(i) for i in route])
    load_ax.set(xlabel="Visited node (route order)", ylabel="Load after service", ylim=(-.3, instance.capacity + 1))
    load_ax.set_title("Capacity at every stop", loc="left", fontweight="bold", color="#20384f", pad=14)
    load_ax.grid(axis="y", alpha=.14); load_ax.legend(frameon=False, fontsize=9)
    for a in (ax, load_ax):
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"{len(instance.requests)}-request example | distance {solution.distance:.4f} ({solution.status})", x=.07, ha="left", fontsize=13, fontweight="bold", color="#20384f")
    fig.tight_layout(rect=(0, 0, 1, .94), w_pad=2.6)
    fig.savefig(path, dpi=180, bbox_inches="tight"); plt.close(fig)


def plot_capacity(rows, path):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    valid = [r for r in rows if r["status"] == "optimal"]
    ax.plot([r["capacity"] for r in valid], [r["distance"] for r in valid], marker="o", color="#178b88", lw=2)
    ax.set(xlabel="Vehicle capacity (load units)", ylabel="Optimal distance (coordinate units)")
    ax.set_title("How much does extra capacity help?", loc="left", fontweight="bold", color="#20384f", pad=14)
    ax.set_xticks([r["capacity"] for r in rows]); ax.spines[["top", "right"]].set_visible(False)
    for row in rows:
        if row["status"] == "infeasible":
            lo, hi = ax.get_ylim()
            ax.text(row["capacity"], lo + .08 * (hi-lo), "Infeasible", ha="center", fontsize=8, color="#607c92")
    ax.grid(alpha=.16)
    fig.tight_layout(); fig.savefig(path, dpi=180); plt.close(fig)
