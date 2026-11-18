"""Phase 4 - Ask the Traffic Analysis Agent a question from the terminal.

Usage:  python ask_analysis.py "Which road has the highest traffic density in the high scenario?"
"""
import sys
from llm import get_llm
from prompts import ANALYSIS_PROMPT
from tools import ANALYSIS_TOOLS
from agent_core import run_agent

question = " ".join(sys.argv[1:]) or "Is PPO performing better than fixed-time control?"
out = run_agent(get_llm(), ANALYSIS_PROMPT, ANALYSIS_TOOLS, question)

print("\n=== TOOL CALLS ===")
for step in out["trace"]:
    print(f"round {step['round']}: {step['tool']}({step['args']})")
print(f"\n=== ANSWER (status: {out['status']}, rounds: {out['rounds']}) ===\n{out['answer']}")