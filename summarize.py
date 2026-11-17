"""Phase 2 - Print mean +/- std per controller and scenario from results/runs.csv."""
import pandas as pd
from config import RUNS_CSV

df = pd.read_csv(RUNS_CSV)
cols = ["avg_wait_s", "avg_queue", "stops_per_vehicle", "throughput"]
g = df.groupby(["controller", "scenario"])[cols].agg(["mean", "std"]).round(2)
print(g.to_string())