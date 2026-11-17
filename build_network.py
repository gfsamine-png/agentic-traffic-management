"""Phase 1 - Build a 4-way intersection (N, S, E, W) with SUMO's netconvert."""
import subprocess
from pathlib import Path

OUT = Path(__file__).parent / "sumo_files"
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

subprocess.run([
    "netconvert",
    "--node-files", str(OUT / "nodes.nod.xml"),
    "--edge-files", str(OUT / "edges.edg.xml"),
    "--output-file", str(OUT / "intersection.net.xml"),
    "--tls.default-type", "static",
    "--no-turnarounds", "true",
], check=True)
print("Network written to", OUT / "intersection.net.xml")