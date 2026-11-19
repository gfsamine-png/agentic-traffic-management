# Traffic analysis report
**Question:** Is the PPO result in the high scenario robust? Confirm it on a new seed and recommend improvements.

## Findings
PPO shows a lower avg_wait_s (48.64 s) and avg_time_loss_s (105.41 s) than fixed‑time (95.42 s, 126.06 s) and actuated (98.15 s, 126.03 s) in the high scenario, but it also has a higher stops_per_vehicle (6.91 vs 3.32/3.47) and a higher pending_end (597.2 vs 526.0/413.4), and its served_pct (80.06 %) is lower than both other controllers.  
**Evidence**  
- fixed_time: avg_wait_s 95.42, avg_time_loss_s 126.06, stops_per_vehicle 3.32, served_pct 81.16, pending_end 526.0  
- actuated: avg_wait_s 98.15, avg_time_loss_s 126.03, stops_per_vehicle 3.47, served_pct 84.5, pending_end 413.4  
- ppo: avg_wait_s 48.64, avg_time_loss_s 105.41, stops_per_vehicle 6.91, served_pct 80.06, pending_end 597.2  
**Likely cause / caveat**  
A likely cause is that PPO’s reward only penalises stopped vehicles inside the network, so it can ignore vehicles that are blocked from entering (high pending_end) and may switch phases more often, leading to more stops per vehicle. To improve robustness, the reward should include pending_end or served_pct, and the safety layer could allow longer green phases to reduce the number of stops.  
**NEEDS_EXPERIMENT: yes**

## Optimization coordinator
- **Robustness confirmed**: seed 6 matches seed 1 (avg_wait 48.33 s vs 48.23 s, avg_time_loss 104.79 s vs 104.8 s, served_pct 80.4 % vs 80.1 %, pending_end 587 vs 598).  
- **Recommendation 1**: modify the PPO reward to include pending_end or served_pct so the policy learns to clear the entrance queue.  
- **Recommendation 2**: relax the safety layer to allow green phases up to 60 s; this should cut stops_per_vehicle (currently 6.86 vs 3.32 for fixed_time) while keeping low wait times.  
- **Recommendation 3**: run a hybrid controller that defaults to actuated when pending_end exceeds a threshold, leveraging actuated’s adaptive green to reduce entrance congestion.

## Experiments requested
- {'controller': 'ppo', 'reason': 'Confirm PPO robustness on a new seed', 'scenario': 'high', 'seed': 6} -> {"status": "completed", "run_id": "exp_ppo_high_s6", "result": {"controller": "ppo", "scenario": "high", "seed": 6, "avg_wait_s": 48.33, "avg_time_los

## Evidence (tool calls)
- get_scenario_summary({'scenario': 'high'})
- list_experiments({})
- run_experiment({'controller': 'ppo', 'reason': 'Confirm PPO robustness on a new seed', 'scenario': 'high', 'seed': 6})
- compare_runs({'run_id_a': 'exp_ppo_high_s6', 'run_id_b': 'ppo_high_s1'})