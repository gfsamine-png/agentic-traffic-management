"""Phase 4 - Results Store: the ONLY place where result files are read or written.

The agents never touch SUMO directly. They read what earlier simulations logged here.
  results/runs.csv         official evaluation (seeds 1-5, all three controllers)
  results/experiments.csv  extra runs requested through the Experiment Runner (seeds 6-50)

All numbers the agents report are computed here, in Python, never by the LLM.
"""
import pandas as pd
from config import RUNS_CSV, RESULTS_DIR

EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"
METRICS = ["avg_wait_s", "avg_time_loss_s", "avg_queue", "stops_per_vehicle",
           "throughput", "served_pct", "pending_end"]
HIGHER_IS_BETTER = {"throughput", "served_pct"}      # for all others, lower is better
ROADS = ["N", "S", "E", "W"]
SIMILAR_PCT = 2.0        # differences below 2 % are reported as "similar"


def load_runs():
    return pd.read_csv(RUNS_CSV) if RUNS_CSV.exists() else pd.DataFrame()


def load_experiments():
    return pd.read_csv(EXPERIMENTS_CSV) if EXPERIMENTS_CSV.exists() else pd.DataFrame()


def append_experiment(row: dict):
    df = pd.DataFrame([row])
    RESULTS_DIR.mkdir(exist_ok=True)
    df.to_csv(EXPERIMENTS_CSV, mode="a", header=not EXPERIMENTS_CSV.exists(), index=False)


def scenario_summary(scenario: str) -> dict:
    """Mean of every metric over the 5 official seeds, per controller."""
    df = load_runs()
    df = df[df["scenario"] == scenario]
    if df.empty:
        return {"error": f"no official results for scenario '{scenario}'"}
    out = {}
    for ctrl, g in df.groupby("controller"):
        out[ctrl] = {"n_seeds": int(len(g)),
                     **{m: round(float(g[m].mean()), 2) for m in METRICS if m in g}}
    return {"scenario": scenario, "controllers": out}


def road_congestion(scenario: str, controller: str) -> dict:
    """Average queue per approach road (N, S, E, W) and which road is the busiest."""
    df = load_runs()
    g = df[(df["scenario"] == scenario) & (df["controller"] == controller)]
    if g.empty:
        return {"error": f"no results for {controller} on {scenario}"}
    q = {r: round(float(g[f"avg_queue_{r}"].mean()), 2) for r in ROADS}
    busiest = max(q, key=q.get)
    return {"scenario": scenario, "controller": controller, "avg_queue_per_road": q,
            "most_congested_road": busiest,
            "share_of_total_queue_pct": round(100 * q[busiest] / max(sum(q.values()), 1e-9), 1)}


def _compare_means(name_a, a: dict, name_b, b: dict) -> dict:
    rows = {}
    for m in METRICS:
        if m not in a or m not in b:
            continue
        va, vb = float(a[m]), float(b[m])
        pct = None if va == 0 else round((vb - va) / va * 100, 1)
        if pct is None or abs(pct) < SIMILAR_PCT:
            verdict = "similar"
        else:
            b_better = (vb > va) if m in HIGHER_IS_BETTER else (vb < va)
            verdict = f"{name_b} better" if b_better else f"{name_a} better"
        rows[m] = {name_a: round(va, 2), name_b: round(vb, 2),
                   f"change_of_{name_b}_vs_{name_a}_pct": pct, "verdict": verdict}
    return rows


def compare_controllers(scenario: str, controller_a: str, controller_b: str) -> dict:
    s = scenario_summary(scenario)
    if "error" in s:
        return s
    c = s["controllers"]
    for name in (controller_a, controller_b):
        if name not in c:
            return {"error": f"no official results for '{name}' on {scenario}"}
    return {"scenario": scenario, "basis": "mean over the official seeds 1-5",
            "metrics": _compare_means(controller_a, c[controller_a], controller_b, c[controller_b])}


def find_run(run_id: str):
    for df, source in ((load_runs(), "official"), (load_experiments(), "experiment")):
        if not df.empty and run_id in set(df["run_id"]):
            return df[df["run_id"] == run_id].iloc[0].to_dict(), source
    return None, None


def compare_runs(run_id_a: str, run_id_b: str) -> dict:
    a, sa = find_run(run_id_a)
    b, sb = find_run(run_id_b)
    for rid, r in ((run_id_a, a), (run_id_b, b)):
        if r is None:
            return {"error": f"run '{rid}' not found"}
    return {"run_a": run_id_a, "run_b": run_id_b, "basis": "single runs",
            "metrics": _compare_means(run_id_a, a, run_id_b, b)}


def list_experiments() -> dict:
    df = load_experiments()
    if df.empty:
        return {"experiments": [], "count": 0}
    cols = ["run_id", "controller", "scenario", "seed", "reason", "avg_wait_s",
            "avg_time_loss_s", "avg_queue", "served_pct"]
    return {"count": int(len(df)), "experiments": df[[c for c in cols if c in df]].to_dict("records")}