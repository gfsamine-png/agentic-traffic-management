"""Phase 1/3 - Build the 4-way intersection with SUMO's netconvert.

Creates two networks with the SAME geometry:
  intersection.net.xml           fixed-time light (our baseline, also used by PPO)
  intersection_actuated.net.xml  SUMO's actuated light (second, stronger baseline)
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent / "sumo_files"
OUT.mkdir(exist_ok=True)
ARM = 200  # length of each road in metres

NODES = f"""<nodes>
  <node id="C" x="0" y="0" type="traffic_light"/>
  <node id="N" x="0" y="{ARM}"/>
  <node id="S" x="0" y="-{ARM}"/>
  <node id="E" x="{ARM}" y="0"/>
  <node id="W" x="-{ARM}" y="0"/>
</nodes>
"""

def edges():
    rows = []
    for a in "NSEW":
        rows.append(f'  <edge id="{a}2C" from="{a}" to="C" numLanes="2" speed="13.89"/>')
        rows.append(f'  <edge id="C2{a}" from="C" to="{a}" numLanes="2" speed="13.89"/>')
    return "<edges>\n" + "\n".join(rows) + "\n</edges>\n"

(OUT / "nodes.nod.xml").write_text(NODES)
(OUT / "edges.edg.xml").write_text(edges())

for tls_type, name in [("static", "intersection.net.xml"),
                       ("actuated", "intersection_actuated.net.xml")]:
    subprocess.run([
        "netconvert",
        "--node-files", str(OUT / "nodes.nod.xml"),
        "--edge-files", str(OUT / "edges.edg.xml"),
        "--output-file", str(OUT / name),
        "--tls.default-type", tls_type,
        "--no-turnarounds", "true",
    ], check=True)
    print("Network written to", OUT / name)