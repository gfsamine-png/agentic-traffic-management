"""Phase 1 - Sanity check: run each scenario through TraCI and print statistics.

Run from anywhere:  python check_setup.py        (add --gui to watch it)
Expects a 'sumo_files' folder next to this script.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import traci

SUMO_DIR = Path(__file__).resolve().parent / "sumo_files"
SCENARIOS = ["low", "medium", "high"]
APPROACHES = ["N", "S", "E", "W"]


def preflight(scenario):
    """Check files and run SUMO once directly so that its real error is visible."""
    cfg = SUMO_DIR / f"{scenario}.sumocfg"
    if not SUMO_DIR.exists():
        sys.exit(f"Folder not found: {SUMO_DIR}\n"
                 "Run build_network.py and generate_traffic.py first, from this folder.")
    for name in ("intersection.net.xml", f"routes_{scenario}.rou.xml", cfg.name):
        if not (SUMO_DIR / name).exists():
            sys.exit(f"Missing file: {SUMO_DIR / name}\n"
                     "Run build_network.py, then generate_traffic.py.")
    if shutil.which("sumo") is None:
        sys.exit("'sumo' not found. Activate your virtual environment "
                 "(.venv\\Scripts\\activate) and run: pip install eclipse-sumo")
    # Short direct run (3 steps): if SUMO fails, we print its own error message.
    result = subprocess.run(["sumo", "-c", str(cfg), "--end", "3"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"SUMO refused to start for scenario '{scenario}':\n"
                 f"{result.stdout}\n{result.stderr}")
    return cfg


def run(scenario, seed=42, gui=False):
    cfg = preflight(scenario)
    binary = "sumo-gui" if gui else "sumo"
    traci.start([binary, "-c", str(cfg), "--seed", str(seed)])
    try:
        arrived = 0
        peak_waiting = 0
        for step in range(3600):
            traci.simulationStep()  # advance 1 simulated second
            arrived += traci.simulation.getArrivedNumber()
            halting = sum(traci.edge.getLastStepHaltingNumber(f"{a}2C") for a in APPROACHES)
            peak_waiting = max(peak_waiting, halting)
            if step % 600 == 599:
                queues = {a: traci.edge.getLastStepHaltingNumber(f"{a}2C") for a in APPROACHES}
                print(f"  t={step + 1:4d}s  vehicles in network={traci.vehicle.getIDCount():3d}  "
                      f"halting={halting:3d}  queue per road={queues}")
        print(f"  -> arrived={arrived}, peak halting vehicles={peak_waiting}")
    finally:
        traci.close()  # always close, even if something fails


if __name__ == "__main__":
    gui = "--gui" in sys.argv
    for s in SCENARIOS:
        print(f"Scenario: {s}")
        run(s, gui=gui)