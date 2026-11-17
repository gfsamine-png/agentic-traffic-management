"""Phase 1 - Generate traffic demand files (one per scenario) and SUMO configs."""
from pathlib import Path

OUT = Path(__file__).parent / "sumo_files"

# Vehicles per hour entering from each approach.
SCENARIOS = {
    "low":    {"N": 300, "S": 300, "E": 300, "W": 300},
    "medium": {"N": 600, "S": 600, "E": 600, "W": 600},
    "high":   {"N": 700, "S": 700, "E": 1100, "W": 1100},  # East-West is busier
}
# Share of vehicles going straight / left / right.
TURN_SHARE = {"straight": 0.6, "left": 0.2, "right": 0.2}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
LEFT = {"N": "E", "E": "S", "S": "W", "W": "N"}   # driving on the right
RIGHT = {v: k for k, v in LEFT.items()}
SIM_END = 3600  # one simulated hour

def route_file(rates):
    lines = ['<routes>',
             '  <vType id="car" accel="2.6" decel="4.5" length="5" maxSpeed="13.89" sigma="0.5"/>']
    for a, vph in rates.items():
        for turn, share in TURN_SHARE.items():
            dest = {"straight": OPPOSITE[a], "left": LEFT[a], "right": RIGHT[a]}[turn]
            lines.append(
                f'  <flow id="{a}_{turn}" type="car" from="{a}2C" to="C2{dest}" '
                f'begin="0" end="{SIM_END}" vehsPerHour="{vph * share:.0f}" '
                f'departLane="best" departSpeed="max" />')
    lines.append('</routes>')
    return "\n".join(lines) + "\n"

def config_file(name):
    return f"""<configuration>
  <input>
    <net-file value="intersection.net.xml"/>
    <route-files value="routes_{name}.rou.xml"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="{SIM_END}"/>
    <step-length value="1"/>
  </time>
  <report>
    <no-step-log value="true"/>
    <no-warnings value="true"/>
  </report>
</configuration>
"""

for name, rates in SCENARIOS.items():
    (OUT / f"routes_{name}.rou.xml").write_text(route_file(rates))
    (OUT / f"{name}.sumocfg").write_text(config_file(name))
    print(f"scenario '{name}': {sum(rates.values())} veh/h total")