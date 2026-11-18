"""Phase 4 - LangChain tools: the ONLY way the LLM agents touch real data.

A LangChain tool is an ordinary Python function plus a name, a description and typed
arguments. The LLM reads the description, decides to call the tool, and fills in the
arguments; LangChain validates them against the type hints (Literal = fixed choices)
and runs the real function. The LLM never executes code or sees SUMO.

Permissions (this is why there are two agents):
  ANALYSIS_TOOLS     read-only
  COORDINATOR_TOOLS  read-only + run_experiment (the only tool that starts a simulation)
"""
from typing import Literal
from langchain_core.tools import tool
import results_store as store
import experiment_runner as runner

Scenario = Literal["low", "medium", "high"]
Controller = Literal["fixed_time", "actuated", "ppo"]


@tool
def get_scenario_summary(scenario: Scenario) -> dict:
    """Mean results over the official seeds 1-5 for EVERY controller (fixed_time, actuated,
    ppo) on one traffic scenario. Metrics: avg_wait_s, avg_time_loss_s, avg_queue,
    stops_per_vehicle, throughput, served_pct, pending_end (vehicles that could not enter
    the network). Use this first to see the overall picture."""
    return store.scenario_summary(scenario)


@tool
def get_road_congestion(scenario: Scenario, controller: Controller) -> dict:
    """Average queue length on each approach road (N, S, E, W) for one controller and
    scenario, and which road is the most congested. Use it to answer 'which road has the
    highest traffic density?' and to explain where congestion comes from."""
    return store.road_congestion(scenario, controller)


@tool
def compare_controllers(scenario: Scenario, controller_a: Controller,
                        controller_b: Controller) -> dict:
    """Compare two controllers on one scenario (official seeds 1-5). Returns, per metric,
    both values, the percentage change of controller_b versus controller_a, and a verdict.
    The percentages are computed in Python, so quote them exactly; never compute your own."""
    return store.compare_controllers(scenario, controller_a, controller_b)


@tool
def list_experiments() -> dict:
    """List the extra experiments already run and logged (run_id, controller, scenario,
    seed, reason, main metrics). Check this BEFORE requesting a new experiment."""
    return store.list_experiments()


@tool
def compare_runs(run_id_a: str, run_id_b: str) -> dict:
    """Compare two single runs by run_id (official ones like 'ppo_high_s1' or experiments
    like 'exp_ppo_high_s7'). Percentages are computed in Python."""
    return store.compare_runs(run_id_a, run_id_b)


@tool
def run_experiment(controller: Controller, scenario: Scenario, seed: int, reason: str) -> dict:
    """Run ONE extra simulation (one hour of traffic) and log it. Allowed: controller in
    fixed_time/actuated/ppo, scenario in low/medium/high, seed an integer from 6 to 50.
    At most 5 new experiments per session; repeating an experiment returns the cached
    result. 'reason' must say why the experiment is needed. Requests outside these limits
    are rejected with an explanation."""
    return runner.run_experiment(controller, scenario, seed, reason, requested_by="coordinator")


ANALYSIS_TOOLS = [get_scenario_summary, get_road_congestion, compare_controllers]
COORDINATOR_TOOLS = [get_scenario_summary, compare_controllers, list_experiments,
                     compare_runs, run_experiment]