"""Phase 5 - The LangGraph workflow that connects both agents.

    START -> analysis ──(needs more evidence?)──► coordinator ──┐
                 │ no                                           ▼
                 └────────────────────────────────────────► report -> END

LangGraph concepts used here:
  * STATE   - one shared dictionary (TrafficState) that every node reads and updates.
  * NODES   - Python functions: take the state, return the fields they changed.
  * EDGES   - fixed arrows between nodes.
  * CONDITIONAL EDGE - a plain-Python function picks the next node (no LLM involved).
The report node is ordinary Python, not a third agent.
"""
import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from agent_core import run_agent
from guard import guard
from prompts import ANALYSIS_PROMPT, COORDINATOR_PROMPT, SYSTEM_FACTS
from tools import ANALYSIS_TOOLS, COORDINATOR_TOOLS
from verify import unverified_numbers

# Questions containing these words are sent to the Coordinator even if the analysis did not ask.
EXPERIMENT_WORDS = ("experiment", "optimi", "improve", "recommend", "robust", "confirm",
                    "new seed", "run ")
FLAG = re.compile(r"^[\s*_`]*NEEDS_EXPERIMENT:\s*(yes|no)[\s*_`.]*$", re.I | re.M)


class TrafficState(TypedDict, total=False):
    question: str
    analysis: str
    analysis_trace: list
    analysis_status: str
    needs_experiment: bool
    coordinator: str
    coordinator_trace: list
    coordinator_status: str
    report: str
    warnings: list


def build_graph(llm):
    # ---- nodes ------------------------------------------------------------
    def analysis_node(state: TrafficState):
        out = run_agent(llm, ANALYSIS_PROMPT, ANALYSIS_TOOLS, state["question"], max_rounds=6)
        text = out["answer"] or ""
        flag = FLAG.search(text)
        needs = bool(flag and flag.group(1).lower() == "yes")
        return {"analysis": FLAG.sub("", text).strip(), "analysis_trace": out["trace"],
                "analysis_status": out["status"], "needs_experiment": needs}

    def coordinator_node(state: TrafficState):
        task = (f"User question: {state['question']}\n\n"
                f"Findings of the Traffic Analysis Agent:\n{state['analysis']}\n\n"
                "Decide whether more evidence is needed, run at most 3 experiments if so, "
                "then give 2-3 recommendations.")
        out = run_agent(llm, COORDINATOR_PROMPT, COORDINATOR_TOOLS, task, max_rounds=6)
        return {"coordinator": out["answer"] or "", "coordinator_trace": out["trace"],
                "coordinator_status": out["status"]}

    def report_node(state: TrafficState):
        trace = state.get("analysis_trace", []) + state.get("coordinator_trace", [])
        sources = [t["result"] for t in trace] + [SYSTEM_FACTS, state["question"]]
        text = state.get("analysis", "") + "\n" + state.get("coordinator", "")
        bad = unverified_numbers(text, sources)
        warnings = []
        if bad:
            warnings.append("Numbers not found in any tool result (check them): "
                            + ", ".join(str(b) for b in bad))
        for who, key in (("analysis agent", "analysis_status"),
                         ("optimization coordinator", "coordinator_status")):
            status = state.get(key)
            if status == "budget_exhausted":
                warnings.append(f"The {who} used its whole tool budget.")
            elif status == "truncated":
                warnings.append(f"The {who}'s answer was cut off by the output limit.")
            elif status == "tool_call_failed":
                warnings.append(f"The {who} could not produce a valid tool call (see Evidence).")

        lines = ["# Traffic analysis report", f"**Question:** {state['question']}", "",
                 "## Findings", state.get("analysis", "(none)")]
        if state.get("coordinator"):
            lines += ["", "## Optimization coordinator", state["coordinator"]]
        experiments = [t for t in state.get("coordinator_trace", []) if t["tool"] == "run_experiment"]
        if experiments:
            lines += ["", "## Experiments requested"]
            lines += [f"- {t['args']} -> {t['result'][:150]}" for t in experiments]
        lines += ["", "## Evidence (tool calls)"]
        lines += [f"- {t['tool']}({t['args']})" for t in trace] or ["- none"]
        if warnings:
            lines += ["", "## Warnings"] + [f"- {w}" for w in warnings]
        return {"report": "\n".join(lines), "warnings": warnings}

    # ---- the conditional edge: plain Python, no LLM ------------------------
    def after_analysis(state: TrafficState):
        asked = any(w in state["question"].lower() for w in EXPERIMENT_WORDS)
        return "coordinator" if (state.get("needs_experiment") or asked) else "report"

    graph = StateGraph(TrafficState)
    graph.add_node("analysis", analysis_node)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("report", report_node)
    graph.add_edge(START, "analysis")
    graph.add_conditional_edges("analysis", after_analysis,
                                {"coordinator": "coordinator", "report": "report"})
    graph.add_edge("coordinator", "report")
    graph.add_edge("report", END)
    return graph.compile()


def ask(llm, question: str) -> TrafficState:
    guard.reset()                      # fresh experiment budget for every user request
    return build_graph(llm).invoke({"question": question})