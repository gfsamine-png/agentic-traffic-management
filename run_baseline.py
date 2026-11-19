"""Run a rule-based traffic-light controller on every scenario and seed,
and save the metrics to results/runs.csv.

Usage:
  python run_baseline.py fixed_time     # SUMO's fixed plan: 42 s NS, 3 s yellow, 42 s EW, 3 s yellow
  python run_baseline.py actuated       # SUMO's actuated plan: green 5-50 s, extended while cars arrive
"""
import csv
import sys
import time
import traci
from config import SUMO_DIR, RESULTS_DIR, RUNS_CSV, SCENARIOS, SEEDS, SIM_SECONDS
from metrics import MetricsCollector

NETWORKS = {"fixed_time": "intersection.net.xml",
            "actuated": "intersection_actuated.net.xml"}


def run_one(controller, scenario, seed):
    cfg = SUMO_DIR / f"{scenario}.sumocfg"
    traci.start(["sumo", "-c", str(cfg), "--seed", str(seed),
                 "--net-file", str(SUMO_DIR / NETWORKS[controller]),
                 "--waiting-time-memory", str(SIM_SECONDS)])
    collector = MetricsCollector()
    try:
        for _ in range(SIM_SECONDS):
            traci.simulationStep()
            collector.update()
    finally:
        traci.close()
    return collector.summary()


def main():
    controller = sys.argv[1] if len(sys.argv) > 1 else "fixed_time"
    if controller not in NETWORKS:
        sys.exit(f"Unknown controller '{controller}'. Use: {', '.join(NETWORKS)}")
    RESULTS_DIR.mkdir(exist_ok=True)
    rows = []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            t0 = time.time()
            res = run_one(controller, scenario, seed)
            row = {"run_id": f"{controller}_{scenario}_s{seed}",
                   "controller": controller, "scenario": scenario, "seed": seed, **res}
            rows.append(row)
            print(f"{row['run_id']:28s} avg_wait={res['avg_wait_s']:7.2f}s  "
                  f"time_loss={res['avg_time_loss_s']:7.2f}s  avg_queue={res['avg_queue']:6.2f}  "
                  f"stops/veh={res['stops_per_vehicle']:.2f}  throughput={res['throughput']}  "
                  f"unfinished={res['unfinished']}  ({time.time() - t0:.0f}s)")

    # Replace earlier rows of this controller, keep the other controllers' rows.
    kept = []
    if RUNS_CSV.exists():
        with open(RUNS_CSV, newline="") as f:
            kept = [r for r in csv.DictReader(f) if r["controller"] != controller]
    fields = list(rows[0].keys())
    with open(RUNS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(kept + rows)
    print(f"\nSaved {len(rows)} runs to {RUNS_CSV}")


if __name__ == "__main__":
    main()