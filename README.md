# Agentic AI-Based Intelligent Traffic Management System (Deep RL)

A simulated 4-way intersection controlled by a **PPO reinforcement-learning agent**, compared
with two classical controllers, and analysed by **two LLM agents** (LangChain + LangGraph)
that read the results, run extra simulations to check them, and write a report. A
**Streamlit dashboard** shows everything.

```
SUMO simulation ──► PPO agent (controls the light) ──► results/*.csv
                                                         │
                 Streamlit dashboard ◄── LangGraph: Analysis agent ─► Coordinator agent
                                         (read-only tools)           (may run new simulations)
```

## Main findings (mean of seeds 1-5, 1 simulated hour per run)

| Scenario | Controller | Avg wait (s) | Time loss (s) | Stops/veh | Served (%) |
|---|---|---|---|---|---|
| Low | Fixed-time | 12.93 | 19.04 | 0.66 | 99.00 |
| Low | Actuated | 2.34 | 7.49 | 0.53 | 99.64 |
| Low | **PPO** | 4.73 | 10.26 | 0.60 | 99.42 |
| Medium | Fixed-time | 18.36 | 27.69 | 1.15 | 98.68 |
| Medium | Actuated | 2.90 | 8.74 | 0.65 | 99.14 |
| Medium | **PPO** | 5.01 | 11.28 | 0.71 | 99.00 |
| High | Fixed-time | 95.42 | 126.06 | 3.32 | 81.16 |
| High | Actuated | 98.15 | 126.03 | 3.47 | 84.50 |
| High | **PPO** | 48.64 | 105.41 | 6.91 | 80.06 |

* **Low / medium traffic:** PPO clearly beats fixed-time (wait -63 % / -73 %, time loss
  -46 % / -59 %), but SUMO's **actuated** controller is better than PPO.
* **High traffic:** PPO halves the measured waiting time and queues, but it makes about twice
  as many stops per vehicle and serves slightly *fewer* vehicles (80.1 % vs 81.2 % fixed-time
  and 84.5 % actuated). Waiting time only counts vehicles that entered the network, so it
  flatters PPO here. See *Limitations*.
* The PPO result is reproducible: a new seed (6) gave wait 48.33 s vs 48.23 s on seed 1.

## Project structure

| File | Role |
|---|---|
| `config.py` | Shared constants: scenarios, seeds, paths |
| `build_network.py` | Builds the intersection with SUMO `netconvert` (static + actuated light) |
| `generate_traffic.py` | Writes the traffic demand and SUMO config for low / medium / high |
| `metrics.py` | Collects wait, time loss, queues, stops, throughput, blocked vehicles via TraCI |
| `run_baseline.py` | Fixed-time and actuated baselines -> `results/runs.csv` |
| `safety.py` | Deterministic safety layer: min green 10 s, yellow 3 s, max green 60 s |
| `gym_env.py` | Gymnasium environment (11 observations, 2 actions, 5 s decisions) |
| `train_ppo.py` | Trains PPO (Stable-Baselines3) -> `models/ppo_traffic.zip` |
| `evaluate.py` | Evaluates PPO on seeds 1-5 -> `results/runs.csv` |
| `summarize.py` | Mean / std tables and PPO change versus each baseline |
| `results_store.py` | Only place where result files are read; computes every number the agents quote |
| `guard.py`, `experiment_runner.py` | Limits and runs extra simulations (seeds 6-50, max 5 per request) |
| `tools.py` | LangChain tools given to the agents |
| `prompts.py`, `agent_core.py` | Agent prompts and the bounded tool-calling loop |
| `verify.py` | Flags numbers in an answer that no tool returned |
| `agent_graph.py` | LangGraph workflow: analysis -> (coordinator) -> report |
| `ask_agents.py`, `ask_analysis.py` | Command-line entry points for the agents |
| `dashboard.py` | Streamlit dashboard |
| `llm.py`, `test_llm.py` | Groq LLM setup and connection test |

## How it works

* **Simulation:** SUMO + TraCI. One intersection, 200 m arms, 2 lanes each. Scenarios:
  low (300 veh/h per approach), medium (600), high (N/S 700, E/W 1100).
* **PPO agent:** one agent. Observation: queue and longest wait on each approach, current
  phase, time in green. Action: give green to North-South or East-West. Reward:
  `-mean halting vehicles / 10 - 0.1 * switch`. The agent only *suggests* a phase; the safety
  layer enforces minimum green, yellow and maximum green.
* **Two LLM agents (Groq, `openai/gpt-oss-20b`):**
  * *Traffic Analysis Agent* - read-only tools, answers questions about the results.
  * *Optimization Coordinator* - may call `run_experiment` to confirm a result on a new seed.
  * Neither agent controls the traffic light. A deterministic guard allows only seeds 6-50 and
    5 experiments per request, and `verify.py` warns about numbers that no tool returned.
* **Evidence:** every report lists the tool calls that produced its numbers.

## Setup

Requirements: Python 3.11+, [SUMO](https://sumo.dlr.de/docs/Downloads.php) (with `netconvert`
and `sumo` on the PATH, and `SUMO_HOME` set), and a free [Groq](https://console.groq.com) API key.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a file named `.env` in the project root (it is git-ignored, never commit it):

```
GROQ_API_KEY=your_key_here
```

## Run, in this order

```powershell
python check_setup.py                 # verifies SUMO + Python packages
python build_network.py               # builds sumo_files/*.net.xml  (folder is git-ignored)
python generate_traffic.py            # builds traffic demand + configs
python run_baseline.py fixed_time     # baseline 1
python run_baseline.py actuated       # baseline 2
python train_ppo.py                   # ~150k steps, creates models/ppo_traffic.zip
python evaluate.py                    # PPO on seeds 1-5
python summarize.py                   # results table
```

Agents and dashboard:

```powershell
python test_llm.py                    # checks the Groq connection
python ask_agents.py "Is PPO better than fixed-time control?"
python ask_agents.py "Is the PPO result in the high scenario robust? Confirm it on a new seed."
streamlit run dashboard.py            # opens http://localhost:8501
```

The report of the last question is saved to `results/reports/latest.md`.

## Limitations

* **PPO's reward ignores vehicles that cannot enter the network.** In the high scenario this
  makes its waiting time look better than its real service (more stops, fewer vehicles
  served). Adding blocked vehicles or throughput to the reward and retraining is the main
  next step.
* PPO does not beat SUMO's actuated controller in low and medium traffic.
* One isolated intersection, one trained model, simulated traffic (no real data), and a
  fixed training budget (150k steps); no hyper-parameter search.
* The LLM agents explain and check results; they do not control the light. Small free models
  can make tool-call mistakes, so the code retries, limits tool use and verifies numbers, but
  the wording of an answer is not guaranteed to be perfect.
* Official results use seeds 1-5; only a few extra seeds were run through the agents.

## Security notes

* `.env` and `sumo_files/` are listed in `.gitignore`. Never commit the API key; if it
  leaks, revoke it in the Groq console and create a new one.

## Technologies

SUMO, TraCI, Gymnasium, Stable-Baselines3 (PPO), PyTorch, LangChain, LangGraph, Groq,
pandas, Streamlit, Altair.
