"""Shared constants. Every script imports from here, so PPO and the baseline
always use exactly the same scenarios, seeds and road names."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMO_DIR = ROOT / "sumo_files"
RESULTS_DIR = ROOT / "results"
RUNS_CSV = RESULTS_DIR / "runs.csv"

SCENARIOS = ["low", "medium", "high"]
SEEDS = [1, 2, 3, 4, 5]
APPROACHES = ["N", "S", "E", "W"]
SIM_SECONDS = 3600