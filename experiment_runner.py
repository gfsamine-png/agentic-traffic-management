"""Phase 4 - Experiment Runner: runs a whitelisted simulation headless and logs it.

Flow: guard.validate -> (cached? return it) -> run SUMO -> append to experiments.csv.
Reuses the SAME code as the official evaluation, so experiments are comparable with it.
"""
import datetime
from config import SIM_SECONDS
import results_store as store
from guard import guard, make_run_id

_ppo_cache = {}


def _simulate(controller, scenario, seed):
    if controller in ("fixed_time", "actuated"):
        from run_baseline import run_one
        return run_one(controller, scenario, seed)
    from stable_baselines3 import PPO
    from config import ROOT
    from gym_env import TrafficEnv
    from evaluate import run_one as run_ppo
    if "model" not in _ppo_cache:
        _ppo_cache["model"] = PPO.load(str(ROOT / "models" / "ppo_traffic"))
        _ppo_cache["env"] = TrafficEnv()
    return run_ppo(_ppo_cache["model"], _ppo_cache["env"], scenario, seed)


def run_experiment(controller, scenario, seed, reason="", requested_by="agent"):
    existing = store.load_experiments()
    done = set(existing["run_id"]) if not existing.empty else set()
    ok, msg = guard.validate(controller, scenario, seed, done)
    if not ok:
        return {"status": "rejected", "reason": msg}
    run_id = make_run_id(controller, scenario, seed)
    if msg == "cached":
        row, _ = store.find_run(run_id)
        return {"status": "cached", "run_id": run_id, "result": _public(row)}
    res = _simulate(controller, scenario, seed)
    row = {"run_id": run_id, "controller": controller, "scenario": scenario, "seed": seed,
           "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
           "requested_by": requested_by, "reason": reason[:200], **res}
    store.append_experiment(row)
    guard.used += 1
    return {"status": "completed", "run_id": run_id, "result": _public(row)}


def _public(row):
    keys = ["controller", "scenario", "seed"] + store.METRICS
    return {k: row[k] for k in keys if k in row}