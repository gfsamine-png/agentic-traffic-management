"""Phase 2 - Run the fixed-time controller on every scenario and seed,
and append the metrics to results/runs.csv.

Usage:  python run_baseline.py
"""
import csv
import time
import traci
from config import SUMO_DIR, RESULTS_DIR, RUNS_CSV, SCENARIOS, SEEDS, SIM_SECONDS
from metrics import MetricsCollector

CONTROLLER = "fixed_time"


def run_one(scenario, seed):
    cfg = SUMO_DIR / f"{scenario}.sumocfg"
    traci.start(["sumo", "-c", str(cfg), "--seed", str(seed),
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
    RESULTS_DIR.mkdir(exist_ok=True)
    rows = []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            t0 = time.time()
            res = run_one(scenario, seed)
            row = {"run_id": f"{CONTROLLER}_{scenario}_s{seed}",
                   "controller": CONTROLLER, "scenario": scenario, "seed": seed, **res}
            rows.append(row)
            print(f"{row['run_id']:28s} avg_wait={res['avg_wait_s']:7.2f}s  "
                  f"avg_queue={res['avg_queue']:6.2f}  stops/veh={res['stops_per_vehicle']:.2f}  "
                  f"throughput={res['throughput']}  ({time.time() - t0:.0f}s)")

    # Overwrite earlier fixed-time rows, keep rows of other controllers (PPO later).
    kept = []
    if RUNS_CSV.exists():
        with open(RUNS_CSV, newline="") as f:
            kept = [r for r in csv.DictReader(f) if r["controller"] != CONTROLLER]
    fields = list(rows[0].keys())
    with open(RUNS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(kept + rows)
    print(f"\nSaved {len(rows)} runs to {RUNS_CSV}")


if __name__ == "__main__":
    main()