"""Phase 5 - Ask the full two-agent system a question and save the report.

Usage:  python ask_agents.py "Is PPO better than fixed-time? Confirm on a new seed."
"""
import sys
from config import RESULTS_DIR
from llm import get_llm
from agent_graph import ask

question = " ".join(sys.argv[1:]) or "Is PPO performing better than fixed-time control?"
state = ask(get_llm(), question)

print(state["report"])
reports = RESULTS_DIR / "reports"
reports.mkdir(parents=True, exist_ok=True)
(reports / "latest.md").write_text(state["report"], encoding="utf-8")
print(f"\n[report saved to {reports / 'latest.md'}]")