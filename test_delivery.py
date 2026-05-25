"""
test_delivery.py – automated test suite for delivery_system.py
Runs the simulator against all provided test cases and the base case.
"""

import json
import math
import sys
from pathlib import Path

# Make sure we can import delivery_system from the same directory
sys.path.insert(0, str(Path(__file__).parent))

from delivery_system import (
    normalise_input,
    assign_packages,
    simulate,
    determine_best_agent,
    euclidean,
)

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def run_test(label: str, input_path: str) -> bool:
    """Run the full pipeline on a single file and print a summary."""
    try:
        with open(input_path) as f:
            raw = json.load(f)

        warehouses, agents, packages = normalise_input(raw)
        assignment = assign_packages(warehouses, agents, packages)
        simulation = simulate(warehouses, agents, assignment)
        best = determine_best_agent(simulation)

        # ---- Validation checks ----
        total_assigned = sum(len(v) for v in assignment.values())
        assert total_assigned == len(packages), (
            f"Package count mismatch: {total_assigned} assigned vs {len(packages)} in input"
        )

        total_delivered = sum(s["packages_delivered"] for s in simulation.values())
        assert total_delivered == len(packages), (
            f"Delivered count mismatch: {total_delivered} vs {len(packages)}"
        )

        # Spot-check distances are non-negative
        for aid, stats in simulation.items():
            assert stats["total_distance"] >= 0, f"Negative distance for {aid}"
            assert stats["efficiency"] >= 0, f"Negative efficiency for {aid}"

        # best_agent must be a real agent key (or N/A if no deliveries)
        if any(s["packages_delivered"] > 0 for s in simulation.values()):
            assert best in agents, f"best_agent '{best}' not in agents dict"

        print(f"{PASS}  {label}")
        print(f"       agents={list(agents.keys())}  packages={len(packages)}")
        for aid, s in simulation.items():
            print(f"       {aid}: delivered={s['packages_delivered']}  "
                  f"dist={s['total_distance']}  eff={s['efficiency']}")
        print(f"       best_agent={best}\n")
        return True

    except Exception as exc:
        print(f"{FAIL}  {label}: {exc}\n")
        return False


def test_euclidean():
    """Unit test for the distance function."""
    assert abs(euclidean([0, 0], [3, 4]) - 5.0) < 1e-9
    assert euclidean([0, 0], [0, 0]) == 0.0
    label = "euclidean distance unit test"
    print(f"{PASS}  {label}")


def test_assignment_nearest():
    """Agent nearest the warehouse gets the package."""
    warehouses = {"W1": [0, 0]}
    agents = {"A1": [1, 0], "A2": [100, 100]}
    packages = [{"id": "P1", "warehouse_id": "W1", "destination": [5, 5]}]
    result = assign_packages(warehouses, agents, packages)
    assert result["A1"] == packages and result["A2"] == []
    print(f"{PASS}  assignment – nearest agent selected")


def test_zero_packages_agent():
    """Agent with no packages has 0 delivered, 0.0 distance, 0.0 efficiency."""
    warehouses = {"W1": [0, 0]}
    agents = {"A1": [1, 0], "A2": [100, 100]}
    packages = [{"id": "P1", "warehouse_id": "W1", "destination": [5, 5]}]
    assignment = assign_packages(warehouses, agents, packages)
    result = simulate(warehouses, agents, assignment)
    assert result["A2"]["packages_delivered"] == 0
    assert result["A2"]["total_distance"] == 0.0
    assert result["A2"]["efficiency"] == 0.0
    print(f"{PASS}  zero-package agent stats are 0")


if __name__ == "__main__":
    print("=" * 55)
    print("FastBox Delivery System – Test Suite")
    print("=" * 55 + "\n")

    # Unit tests
    test_euclidean()
    test_assignment_nearest()
    test_zero_packages_agent()
    print()

    # Integration tests against all provided JSON files
    base = Path(__file__).parent.parent / "assignment"
    test_dir = base / "Python Assignment(Delivery System Test Cases)"

    results = []
    results.append(run_test("base_case.json", base / "base_case.json"))
    for i in range(1, 11):
        tc = test_dir / f"test_case_{i}.json"
        if tc.exists():
            results.append(run_test(f"test_case_{i}.json", tc))
        else:
            print(f"⚠️  SKIP  test_case_{i}.json (file not found)")

    passed = sum(results)
    total = len(results)
    print("=" * 55)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)
