# FastBox Delivery System – Python Assignment

## Overview
Simulates one day of logistics operations for FastBox: assigns packages to agents,
computes delivery distances, and produces a ranked performance report.

---

## Project Structure

```
fastbox_delivery/
├── delivery_system.py   # Core simulator (main entry point)
├── test_delivery.py     # Automated test suite (unit + integration)
├── data.json            # Sample input (base_case)
├── report.json          # Generated output (auto-created on run)
└── top_performer.csv    # Bonus: CSV export of best agent
```

---

## Requirements

Python 3.10+ (uses `list[...]` type hints).  
**No external dependencies** – only the standard library (`json`, `math`,
`random`, `csv`, `argparse`, `pathlib`).

---

## Usage

```bash
# Basic run (reads data.json, writes report.json)
python3 delivery_system.py

# Custom input/output paths
python3 delivery_system.py path/to/input.json -o path/to/report.json

# With random delivery delays (bonus feature)
python3 delivery_system.py data.json --delays

# Run all tests (unit + integration)
python3 test_delivery.py
```

---

## Algorithm

### 1. Input Parsing
The system handles **two JSON formats** observed in the test cases:
- **Dict format**: `{"warehouses": {"W1": [x, y]}}`
- **List format**: `{"warehouses": [{"id": "W1", "location": [x, y]}]}`

Package keys `"warehouse"` and `"warehouse_id"` are both accepted.

### 2. Package–Agent Assignment
Each package is independently assigned to the agent with the smallest
**Euclidean distance** to that package's warehouse.

```
distance(agent, warehouse) = √((x₂-x₁)² + (y₂-y₁)²)
```

### 3. Delivery Simulation
For each agent, deliveries are processed one at a time:

```
agent → warehouse (pick up) → destination (deliver)
```

The agent's position is updated after each delivery leg. Total distance is
the sum of all such legs.

### 4. Report Generation

| Field               | Description                                 |
|---------------------|---------------------------------------------|
| `packages_delivered`| Count of packages assigned to this agent   |
| `total_distance`    | Sum of all travel distances (rounded 2 dp)  |
| `efficiency`        | `total_distance / packages_delivered`       |
| `best_agent`        | Agent with **lowest** efficiency score      |

Agents with zero deliveries have `efficiency = 0.0`.

---

## Bonus Features

| Feature                | Description                                    |
|------------------------|------------------------------------------------|
| **Random delays**      | `--delays` flag adds 0–30% random distance overhead per leg |
| **ASCII route map**    | Printed to stdout after each run               |
| **CSV export**         | `top_performer.csv` saved alongside report     |

---

## Assumptions & Design Decisions

1. **Input format flexibility**: Both dict and list formats are supported
   (observed across provided test cases). Package key `"warehouse"` and
   `"warehouse_id"` are both valid.

2. **Greedy assignment**: Packages are assigned independently (not globally
   optimised). This is O(P × A) and straightforward to reason about.

3. **Route model**: "Pick one, deliver one" – the agent travels to a warehouse,
   picks up a package, delivers it, then moves to the next warehouse. This avoids
   the NP-hard multi-stop routing problem while staying realistic.

4. **Efficiency = distance / packages**: Lower is better. This matches the
   sample output in the assignment PDF.

5. **Best agent tie-breaking**: Ties are broken alphabetically by agent ID
   (deterministic and predictable).

6. **Zero-package agents**: Included in the report with zeros; excluded from
   best-agent selection to avoid division-by-zero.

7. **Delay model (bonus)**: A random multiplier in [1.0, 1.30] is applied to
   each distance leg, simulating real-world traffic or handling delays.

---

## Test Results

All 11 provided test cases pass validation:

```
✅ base_case.json
✅ test_case_1.json  … test_case_10.json
Results: 11/11 tests passed
```

Validation checks per test:
- Total packages assigned = total packages in input
- Total packages delivered = total packages in input  
- All distances and efficiencies are non-negative
- `best_agent` is a valid agent ID

---

## Sample Output (base_case.json)

```json
{
  "A1": { "packages_delivered": 2, "total_distance": 121.21, "efficiency": 60.61 },
  "A2": { "packages_delivered": 2, "total_distance": 79.21,  "efficiency": 39.60 },
  "A3": { "packages_delivered": 1, "total_distance": 14.14,  "efficiency": 14.14 },
  "best_agent": "A3"
}
```
