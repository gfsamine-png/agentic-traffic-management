"""Phase 4 - Guard: deterministic validation of every experiment request.

The Optimization Coordinator (an LLM) can only ASK for an experiment. This plain-Python
check decides whether it is allowed. No LLM is involved, so a hallucinated or hostile
request cannot start anything outside the whitelist.
"""
from config import SCENARIOS

ALLOWED_CONTROLLERS = ["fixed_time", "actuated", "ppo"]
SEED_MIN, SEED_MAX = 6, 50      # seeds 1-5 = official evaluation, 100+ = PPO training
MAX_EXPERIMENTS_PER_SESSION = 5


def make_run_id(controller, scenario, seed):
    return f"exp_{controller}_{scenario}_s{seed}"


class ExperimentGuard:
    def __init__(self, max_experiments=MAX_EXPERIMENTS_PER_SESSION):
        self.max_experiments = max_experiments
        self.used = 0

    def reset(self):
        self.used = 0

    def validate(self, controller, scenario, seed, already_done: set):
        if controller not in ALLOWED_CONTROLLERS:
            return False, f"controller must be one of {ALLOWED_CONTROLLERS}"
        if scenario not in SCENARIOS:
            return False, f"scenario must be one of {SCENARIOS}"
        if not isinstance(seed, int) or not (SEED_MIN <= seed <= SEED_MAX):
            return False, (f"seed must be an integer between {SEED_MIN} and {SEED_MAX} "
                           "(seeds 1-5 are the official evaluation)")
        if make_run_id(controller, scenario, seed) in already_done:
            return True, "cached"                      # same experiment already logged
        if self.used >= self.max_experiments:
            return False, f"experiment budget reached ({self.max_experiments} per session)"
        return True, "ok"


guard = ExperimentGuard()