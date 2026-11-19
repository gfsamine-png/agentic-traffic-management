"""Phase 6 - Streamlit dashboard.

Run:  streamlit run dashboard.py

Four tabs:
  Results       PPO vs fixed-time vs actuated: KPI cards, comparison chart, full table
  Roads         average queue on each approach road
  Ask the agents  type a question -> LangGraph (Analysis + Coordinator) -> report + evidence
  Experiments   extra simulations the Coordinator ran (seeds 6-50)

Every number shown comes from results/runs.csv and results/experiments.csv. The LLM is only
used in the 'Ask the agents' tab, and its report lists the tool calls that produced its numbers.
"""
import altair as alt
import pandas as pd
import streamlit as st

import results_store as store
from config import SCENARIOS

st.set_page_config(page_title="Agentic Traffic Management", page_icon="🚦", layout="wide")

CONTROLLERS = ["fixed_time", "actuated", "ppo"]
LABELS = {"fixed_time": "Fixed-time", "actuated": "Actuated", "ppo": "PPO (RL)"}
METRIC_LABELS = {
    "avg_wait_s": "Average wait (s)",
    "avg_time_loss_s": "Average time loss (s)",
    "avg_queue": "Average queue (vehicles)",
    "stops_per_vehicle": "Stops per vehicle",
    "throughput": "Throughput (vehicles finished)",
    "served_pct": "Served (%)",
    "pending_end": "Vehicles blocked at entrance (end)",
}
HIGHER_BETTER = store.HIGHER_IS_BETTER

QUESTIONS = [
    "Is PPO better than fixed-time control?",
    "Compare PPO and actuated in the high scenario",
    "Which road is the most congested in the high scenario under PPO?",
    "Is the PPO result in the high scenario robust? Confirm it on a new seed and "
    "recommend improvements.",
]


@st.cache_data(ttl=5)
def load_means() -> pd.DataFrame:
    runs = store.load_runs()
    if runs.empty:
        return runs
    cols = [m for m in store.METRICS if m in runs.columns]
    return runs.groupby(["scenario", "controller"])[cols].mean().round(2).reset_index()


def pct_change(new, old):
    return None if old in (0, None) else (new - old) / old * 100


def grouped_bars(wide: pd.DataFrame, order: list, y_title: str):
    """Side-by-side bars: one group per row of `wide`, one bar per column, fixed order."""
    long = wide.reset_index(names="group").melt("group", var_name="series", value_name="value")
    chart = (alt.Chart(long).mark_bar()
             .encode(x=alt.X("group:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
                     xOffset=alt.XOffset("series:N", sort=list(wide.columns)),
                     y=alt.Y("value:Q", title=y_title),
                     color=alt.Color("series:N", sort=list(wide.columns), title=None),
                     tooltip=["group", "series", "value"])
             .properties(height=320))
    st.altair_chart(chart, width="stretch")


means = load_means()

st.title("🚦 Agentic AI Traffic Management")
st.caption("One PPO agent controls the light (SUMO). Two LLM agents analyse the results and "
           "request extra simulations (LangGraph).")

if means.empty:
    st.error("No results found. Run run_baseline.py (fixed_time, actuated) and evaluate.py first.")
    st.stop()

tab_res, tab_roads, tab_ask, tab_exp = st.tabs(
    ["📊 Results", "🛣️ Roads", "💬 Ask the agents", "🧪 Experiments"])

# --------------------------------------------------------------------- Results
with tab_res:
    scenario = st.radio("Traffic scenario", SCENARIOS, horizontal=True, index=2,
                        format_func=str.capitalize)
    sub = means[means["scenario"] == scenario].set_index("controller")
    have = [c for c in CONTROLLERS if c in sub.index]

    if "ppo" in have and "fixed_time" in have:
        st.subheader("PPO versus fixed-time (mean of seeds 1-5)")
        cols = st.columns(5)
        for col, m in zip(cols, ["avg_wait_s", "avg_time_loss_s", "avg_queue",
                                 "stops_per_vehicle", "served_pct"]):
            if m not in sub.columns:
                continue
            new, old = sub.loc["ppo", m], sub.loc["fixed_time", m]
            ch = pct_change(new, old)
            col.metric(METRIC_LABELS[m], f"{new:g}",
                       None if ch is None else f"{ch:+.0f}% vs fixed-time",
                       delta_color="normal" if m in HIGHER_BETTER else "inverse")
    if scenario == "high":
        st.warning(
            "**Read the high scenario with care.** PPO cuts waiting and queues, but it makes "
            "more stops per vehicle and serves fewer vehicles (more are blocked at the "
            "entrance). Waiting time only counts vehicles that entered the network, so it "
            "looks better than the real service. Check *served %* and *blocked at entrance*.")

    st.subheader("Comparison chart")
    metric = st.selectbox("Metric", [m for m in METRIC_LABELS if m in means.columns],
                          format_func=METRIC_LABELS.get)
    arrow = "higher is better" if metric in HIGHER_BETTER else "lower is better"
    st.caption(f"{METRIC_LABELS[metric]} - {arrow}")
    chart = (means.pivot(index="scenario", columns="controller", values=metric)
             .reindex(SCENARIOS)[[c for c in CONTROLLERS if c in set(means["controller"])]]
             .rename(columns=LABELS))
    chart.index = [i.capitalize() for i in chart.index]
    grouped_bars(chart, [i.capitalize() for i in SCENARIOS], METRIC_LABELS[metric])

    st.subheader(f"All metrics - {scenario} scenario")
    table = (sub.loc[have, [m for m in METRIC_LABELS if m in sub.columns]]
             .rename(index=LABELS, columns=METRIC_LABELS))
    st.dataframe(table, width="stretch")

# ----------------------------------------------------------------------- Roads
with tab_roads:
    runs = store.load_runs()
    c1, c2 = st.columns(2)
    sc = c1.selectbox("Scenario", SCENARIOS, index=2, key="road_sc")
    present = [c for c in CONTROLLERS if c in set(runs["controller"])]
    data = {}
    for ctrl in present:
        r = store.road_congestion(sc, ctrl)
        if "avg_queue_per_road" in r:
            data[LABELS[ctrl]] = r["avg_queue_per_road"]
    if data:
        grouped_bars(pd.DataFrame(data).reindex(store.ROADS), store.ROADS,
                     "Average stopped vehicles")
        st.caption("Average number of stopped vehicles on each approach road "
                   "(N, S = vertical; E, W = horizontal).")
    else:
        st.info("No per-road data in runs.csv.")

# ------------------------------------------------------------------ Ask agents
with tab_ask:
    st.write("Ask a question. The **Traffic Analysis Agent** reads the results with read-only "
             "tools; the **Optimization Coordinator** may run up to 3 extra simulations "
             "(seeds 6-50) to check a result.")
    st.session_state.setdefault("question", QUESTIONS[0])
    for i, q in enumerate(QUESTIONS):
        if st.button(q, key=f"q{i}", width="stretch"):
            st.session_state["question"] = q
    question = st.text_area("Your question", key="question", height=70)

    if st.button("Ask", type="primary"):
        try:
            from agent_graph import ask
            from llm import get_llm
            with st.spinner("The agents are working (a robustness check runs a real "
                            "simulation, ~1 minute)..."):
                st.session_state["state"] = ask(get_llm(), question)
            load_means.clear()
        except Exception as exc:      # missing key, no network, rate limit...
            st.session_state.pop("state", None)
            st.error(f"The agents could not answer: {exc}")

    state = st.session_state.get("state")
    if state:
        for w in state.get("warnings", []):
            st.warning(w)
        st.markdown("### Findings")
        st.markdown(state.get("analysis", ""))
        if state.get("coordinator"):
            st.markdown("### Optimization coordinator")
            st.markdown(state["coordinator"])
        with st.expander("Evidence: tool calls and their results"):
            for who, key in (("Analysis agent", "analysis_trace"),
                             ("Coordinator", "coordinator_trace")):
                for t in state.get(key, []):
                    st.markdown(f"**{who}** -> `{t['tool']}({t['args']})`")
                    st.code(str(t["result"])[:1500], language="json")
        st.download_button("Download report (.md)", state["report"],
                           file_name="traffic_report.md")

# ----------------------------------------------------------------- Experiments
with tab_exp:
    exp = store.load_experiments()
    if exp.empty:
        st.info("No extra experiments yet. Ask the agents to confirm a result on a new seed.")
    else:
        keep = ["run_id", "controller", "scenario", "seed", "avg_wait_s", "avg_time_loss_s",
                "avg_queue", "stops_per_vehicle", "served_pct", "pending_end", "reason"]
        st.dataframe(exp[[c for c in keep if c in exp.columns]], width="stretch")
        st.caption("Logged by the Experiment Runner. The Coordinator cannot run official "
                   "seeds 1-5 and is limited to 5 new simulations per request.")