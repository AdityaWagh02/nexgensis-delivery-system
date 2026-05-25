"""
FastBox Delivery System Simulator
==================================
Simulates one day of logistics operations for the FastBox delivery company.

Key Design Decisions / Assumptions (as required by assignment instructions):
1. Input format flexibility: The system handles BOTH input formats found in the
   test cases:
     - Dict format:  {"warehouses": {"W1": [x, y], ...}, "agents": {"A1": [x, y], ...}}
     - List format:  {"warehouses": [{"id": "W1", "location": [x, y]}, ...], ...}
   Package fields accept both "warehouse" and "warehouse_id" keys.

2. Agent-package assignment: Each package is independently assigned to the
   nearest agent (by Euclidean distance from agent's current position to
   warehouse). This is a greedy per-package assignment, not a global optimum.

3. Delivery route per agent: An agent may hold multiple packages. They travel
   to each warehouse in the order packages were assigned, pick up the package,
   then immediately deliver it to the destination before moving to the next
   warehouse. This "pick-one-deliver-one" model avoids the NP-hard routing
   problem while remaining realistic.
   Total distance per agent = sum of (agent→warehouse + warehouse→destination)
   for all assigned packages, where the agent's position updates after each
   delivery.

4. Efficiency metric: efficiency = total_distance / packages_delivered
   (average distance per package, lower is better). This matches the sample
   output format in the assignment.

5. Best agent: the agent with the LOWEST efficiency score (least distance per
   package). Ties broken by alphabetical agent ID.

6. Agents with zero packages are included in the report with 0 delivered,
   0.0 distance, and efficiency = 0.0 (not undefined / division-by-zero).

7. Random delays (bonus): optional, off by default; pass --delays flag to CLI.

8. ASCII route visualisation (bonus): printed to stdout after the report.

9. CSV export of top performer (bonus): saved alongside report.json as
   top_performer.csv.
"""

import json
import math
import random
import csv
import argparse
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def euclidean(p1: list[float], p2: list[float]) -> float:
    """Return Euclidean distance between two 2-D points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# ---------------------------------------------------------------------------
# Input parsing  –  handles both dict and list formats
# ---------------------------------------------------------------------------

def normalise_input(data: dict) -> tuple[dict, dict, list[dict]]:
    """
    Parse the raw JSON data into three uniform structures:
      warehouses : {id: [x, y]}
      agents     : {id: [x, y]}
      packages   : [{"id": ..., "warehouse_id": ..., "destination": [x, y]}]

    Supports both input formats observed in the test cases.
    """
    raw_wh = data["warehouses"]
    raw_ag = data["agents"]
    raw_pk = data["packages"]

    # -- Warehouses --
    if isinstance(raw_wh, dict):
        warehouses = {wid: list(loc) for wid, loc in raw_wh.items()}
    else:
        # list of {"id": "W1", "location": [x, y]}
        warehouses = {w["id"]: list(w["location"]) for w in raw_wh}

    # -- Agents --
    if isinstance(raw_ag, dict):
        agents = {aid: list(loc) for aid, loc in raw_ag.items()}
    else:
        agents = {a["id"]: list(a["location"]) for a in raw_ag}

    # -- Packages --
    packages = []
    for p in raw_pk:
        wh_key = p.get("warehouse") or p.get("warehouse_id")
        packages.append({
            "id": p["id"],
            "warehouse_id": wh_key,
            "destination": list(p["destination"]),
        })

    return warehouses, agents, packages


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def assign_packages(
    warehouses: dict,
    agents: dict,
    packages: list[dict],
) -> dict[str, list[dict]]:
    """
    Assign each package to the agent nearest (Euclidean) to that package's
    warehouse.  Returns a mapping {agent_id: [package, ...]}.
    """
    assignment: dict[str, list[dict]] = {aid: [] for aid in agents}

    for pkg in packages:
        wh_loc = warehouses[pkg["warehouse_id"]]
        # Find agent with minimum distance to the warehouse
        nearest = min(
            agents.keys(),
            key=lambda aid: euclidean(agents[aid], wh_loc),
        )
        assignment[nearest].append(pkg)

    return assignment


def simulate(
    warehouses: dict,
    agents: dict,
    assignment: dict[str, list[dict]],
    use_delays: bool = False,
) -> dict[str, dict]:
    """
    Simulate deliveries and compute per-agent statistics.

    Route model: agent travels to warehouse → delivers to destination → repeats.
    Agent position updates after each delivery.

    Returns a dict {agent_id: {"packages_delivered": int, "total_distance": float,
                                "efficiency": float, "route": [...]}}.
    """
    report: dict[str, dict] = {}

    for aid, pkgs in assignment.items():
        pos = list(agents[aid])   # mutable current position
        total_dist = 0.0
        route = [list(pos)]       # for ASCII visualisation (bonus)

        for pkg in pkgs:
            wh_loc = warehouses[pkg["warehouse_id"]]
            dest = pkg["destination"]

            # Leg 1: agent → warehouse
            d_to_wh = euclidean(pos, wh_loc)

            # Optional random delay (bonus feature)
            if use_delays:
                delay_factor = random.uniform(1.0, 1.3)  # 0–30% extra
                d_to_wh *= delay_factor

            total_dist += d_to_wh
            pos = list(wh_loc)
            route.append(list(pos))

            # Leg 2: warehouse → destination
            d_to_dest = euclidean(pos, dest)
            if use_delays:
                d_to_dest *= random.uniform(1.0, 1.3)

            total_dist += d_to_dest
            pos = list(dest)
            route.append(list(pos))

        delivered = len(pkgs)
        efficiency = round(total_dist / delivered, 2) if delivered > 0 else 0.0

        report[aid] = {
            "packages_delivered": delivered,
            "total_distance": round(total_dist, 2),
            "efficiency": efficiency,
            "route": route,              # kept for bonus ASCII map; not written to JSON
        }

    return report


def determine_best_agent(report: dict[str, dict]) -> str:
    """
    Best agent = lowest efficiency score (average distance per package).
    Only agents who delivered at least one package are considered.
    Ties broken alphabetically by agent ID.
    """
    candidates = {
        aid: stats for aid, stats in report.items()
        if stats["packages_delivered"] > 0
    }
    if not candidates:
        return "N/A"
    return min(candidates.keys(), key=lambda aid: (candidates[aid]["efficiency"], aid))


# ---------------------------------------------------------------------------
# Bonus: ASCII route visualisation
# ---------------------------------------------------------------------------

def ascii_map(
    warehouses: dict,
    agents: dict,
    assignment: dict[str, list[dict]],
    report: dict[str, dict],
    width: int = 60,
    height: int = 25,
) -> str:
    """Render a simple ASCII map of all warehouse/destination positions."""
    # Collect all coordinates
    all_x = [loc[0] for loc in warehouses.values()] + \
            [loc[0] for loc in agents.values()]
    all_y = [loc[1] for loc in warehouses.values()] + \
            [loc[1] for loc in agents.values()]

    for _, pkgs in assignment.items():
        for p in pkgs:
            all_x.append(p["destination"][0])
            all_y.append(p["destination"][1])

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    range_x = max(max_x - min_x, 1)
    range_y = max(max_y - min_y, 1)

    def scale(x, y):
        col = int((x - min_x) / range_x * (width - 1))
        row = int((max_y - y) / range_y * (height - 1))   # flip Y
        return row, col

    grid = [["." for _ in range(width)] for _ in range(height)]

    # Plot warehouses as 'W'
    for wid, loc in warehouses.items():
        r, c = scale(*loc)
        grid[r][c] = "W"

    # Plot agents as 'A'
    for aid, loc in agents.items():
        r, c = scale(*loc)
        grid[r][c] = "A"

    # Plot destinations as 'D'
    for _, pkgs in assignment.items():
        for p in pkgs:
            r, c = scale(*p["destination"])
            if grid[r][c] == ".":
                grid[r][c] = "D"

    lines = ["ASCII Route Map", "=" * width]
    lines += ["".join(row) for row in grid]
    lines += [
        "=" * width,
        "  W = Warehouse   A = Agent (start)   D = Delivery destination",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bonus: CSV export of top performer
# ---------------------------------------------------------------------------

def export_top_performer_csv(
    agent_id: str,
    stats: dict,
    output_path: Path,
) -> None:
    """Write the top-performer row to a CSV file."""
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["agent_id", "packages_delivered", "total_distance", "efficiency"],
        )
        writer.writeheader()
        writer.writerow({
            "agent_id": agent_id,
            "packages_delivered": stats["packages_delivered"],
            "total_distance": stats["total_distance"],
            "efficiency": stats["efficiency"],
        })


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(input_path: str, output_path: str, use_delays: bool = False) -> dict:
    """
    Full pipeline: read → parse → assign → simulate → report → save.
    Returns the final report dict (useful for testing).
    """
    # 1. Read and parse input JSON
    with open(input_path, "r") as f:
        raw = json.load(f)

    warehouses, agents, packages = normalise_input(raw)

    # 2. Assign packages to nearest agents
    assignment = assign_packages(warehouses, agents, packages)

    # 3. Simulate deliveries
    simulation = simulate(warehouses, agents, assignment, use_delays=use_delays)

    # 4. Determine the best agent
    best = determine_best_agent(simulation)

    # 5. Build the final report (strip internal 'route' key from JSON output)
    final_report: dict[str, Any] = {}
    for aid, stats in simulation.items():
        final_report[aid] = {
            "packages_delivered": stats["packages_delivered"],
            "total_distance": stats["total_distance"],
            "efficiency": stats["efficiency"],
        }
    final_report["best_agent"] = best

    # 6. Save report.json
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n✅  Report saved → {out}")
    print(json.dumps(final_report, indent=2))

    # --- Bonus: ASCII map ---
    print("\n" + ascii_map(warehouses, agents, assignment, simulation))

    # --- Bonus: CSV export of top performer ---
    if best != "N/A":
        csv_path = out.parent / "top_performer.csv"
        export_top_performer_csv(best, simulation[best], csv_path)
        print(f"\n🏆  Top performer CSV saved → {csv_path}")

    return final_report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FastBox Delivery System Simulator",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="data.json",
        help="Path to input JSON file (default: data.json)",
    )
    parser.add_argument(
        "-o", "--output",
        default="report.json",
        help="Path for the output report JSON (default: report.json)",
    )
    parser.add_argument(
        "--delays",
        action="store_true",
        help="[Bonus] Simulate random delivery delays (adds 0–30%% to distances)",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"❌  Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    run(args.input, args.output, use_delays=args.delays)
