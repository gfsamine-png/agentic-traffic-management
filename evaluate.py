"""Phase 3 - Evaluate the trained PPO on the same scenarios and seeds as the baseline.
Appends the rows to results/runs.csv (controller = 'ppo').

Usage:  python evaluate.py
"""
import csv
import time
from stable_baselines3 import PPO
from config import ROOT, RESULTS_DIR, RUNS_CSV, SCENARIOS, SEEDS
from gym_env import TrafficEnv
from metrics import MetricsCollector

CONTROLLER = "ppo"


def run_one(model, env, scenario, seed):
    collector = MetricsCollector()
    env.on_sim_step = collector.update            # same metrics code as the baseline
    obs, _ = env.reset(options={"scenario": scenario, "seed": seed})
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, _, done, _ = env.step(action)
    env.close()
    return collector.summary()


def main():
    model = PPO.load(str(ROOT / "models" / "ppo_traffic"))
    env = TrafficEnv()
    rows = []
    for scenario in SCENARIOS:
        for seed in SEEDS:
            t0 = time.time()
            res = run_one(model, env, scenario, seed)
            row = {"run_id": f"{CONTROLLER}_{scenario}_s{seed}", "controller": CONTROLLER,
                   "scenario": scenario, "seed": seed, **res}
            rows.append(row)
            print(f"{row['run_id']:28s} avg_wait={res['avg_wait_s']:7.2f}s  "
                  f"avg_queue={res['avg_queue']:6.2f}  stops/veh={res['stops_per_vehicle']:.2f}  "
                  f"throughput={res['throughput']}  ({time.time() - t0:.0f}s)")
    kept = []
    if RUNS_CSV.exists():
        with open(RUNS_CSV, newline="") as f:
            kept = [r for r in csv.DictReader(f) if r["controller"] != CONTROLLER]
    with open(RUNS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(kept + rows)
    print(f"\nSaved {len(rows)} runs to {RUNS_CSV}")


if __name__ == "__main__":
    main()