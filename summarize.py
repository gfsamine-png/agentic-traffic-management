"""Print mean +/- std per controller and scenario from results/runs.csv,
then PPO's change versus each baseline."""
import pandas as pd
from config import RUNS_CSV

df = pd.read_csv(RUNS_CSV)
cols = ["avg_wait_s", "avg_time_loss_s", "avg_queue", "stops_per_vehicle", "throughput", "unfinished", "pending_end", "served_pct"]
cols = [c for c in cols if c in df.columns]
mean = df.groupby(["scenario", "controller"])[cols].mean()
std = df.groupby(["scenario", "controller"])[cols].std()
order = {"low": 0, "medium": 1, "high": 2}
mean = mean.sort_index(key=lambda idx: idx.map(order) if idx.name == "scenario" else idx)

print("=== MEAN over seeds ===")
print(mean.round(2).to_string())
print("\n=== STD over seeds ===")
print(std.reindex(mean.index).round(2).to_string())

print("\n=== PPO change versus each baseline (negative = PPO better, except throughput) ===")
rows = []
for sc in ["low", "medium", "high"]:
    for base in ["fixed_time", "actuated"]:
        if (sc, "ppo") in mean.index and (sc, base) in mean.index:
            p, b = mean.loc[(sc, "ppo")], mean.loc[(sc, base)]
            rows.append({"scenario": sc, "vs": base,
                         **{c: f"{(p[c] - b[c]) / b[c] * 100:+.0f}%" if b[c] else "n/a" for c in cols}})
print(pd.DataFrame(rows).to_string(index=False))