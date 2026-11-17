"""Phase 3 - Gymnasium environment that lets PPO control the SUMO traffic light.

reset()  -> start a new simulated hour (random scenario + seed during training)
step(a)  -> apply PPO's action through the safety logic, advance SUMO 5 s,
            return (observation, reward, terminated, truncated, info)
"""
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import traci

from config import SUMO_DIR, APPROACHES, SIM_SECONDS
from safety import SignalSafety, YELLOW, NS, EW

DECISION_INTERVAL = 5          # simulated seconds between PPO decisions
MAX_QUEUE = 40                 # normalisation constants for the observation
MAX_WAIT = 120
MAX_GREEN_NORM = 60
SWITCH_PENALTY = 0.1
TRAIN_SCENARIOS = ["low", "medium", "high"]
TRAIN_WEIGHTS = [0.2, 0.3, 0.5]    # high traffic matters most
TRAIN_SEED_START = 100             # evaluation uses seeds 1-5, never seen in training


class TrafficEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.action_space = spaces.Discrete(2)                       # 0 = NS green, 1 = EW green
        self.observation_space = spaces.Box(0.0, 1.0, shape=(11,), dtype=np.float32)
        self.safety = SignalSafety()
        self.on_sim_step = None      # optional callback after every simulated second
        self.connected = False
        self.episode_count = 0
        self.t = 0
        self.rng = random.Random(0)

    # ---- helpers -------------------------------------------------------
    def _close(self):
        if self.connected:
            try:
                traci.close()
            except Exception:
                pass
            self.connected = False

    def _queues(self):
        return [traci.edge.getLastStepHaltingNumber(f"{a}2C") for a in APPROACHES]

    def _max_waits(self):
        out = []
        for a in APPROACHES:
            ids = traci.edge.getLastStepVehicleIDs(f"{a}2C")
            out.append(max((traci.vehicle.getWaitingTime(v) for v in ids), default=0.0))
        return out

    def _observe(self):
        q = np.clip(np.array(self._queues()) / MAX_QUEUE, 0, 1)
        w = np.clip(np.array(self._max_waits()) / MAX_WAIT, 0, 1)
        phase = np.array([1.0, 0.0] if self.safety.current == NS else [0.0, 1.0])
        g = np.array([min(self.safety.time_in_green / MAX_GREEN_NORM, 1.0)])
        return np.concatenate([q, w, phase, g]).astype(np.float32)

    def _sim_second(self):
        traci.simulationStep()
        if self.on_sim_step:
            self.on_sim_step()
        return sum(self._queues())

    # ---- Gymnasium API -------------------------------------------------
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._close()
        options = options or {}
        if "scenario" in options:                       # evaluation: fixed scenario + seed
            scenario, sumo_seed = options["scenario"], options["seed"]
        else:                                           # training: random scenario + new seed
            scenario = self.rng.choices(TRAIN_SCENARIOS, TRAIN_WEIGHTS)[0]
            sumo_seed = TRAIN_SEED_START + self.episode_count
        self.episode_count += 1
        traci.start(["sumo", "-c", str(SUMO_DIR / f"{scenario}.sumocfg"),
                     "--seed", str(sumo_seed), "--waiting-time-memory", str(SIM_SECONDS)])
        self.connected = True
        self.safety.reset()
        self.t = 0
        self.scenario = scenario
        return self._observe(), {"scenario": scenario}

    def step(self, action):
        action = int(action)
        halting_total = 0
        switched = self.safety.decide(action)
        seconds_left = DECISION_INTERVAL
        if switched:
            self.safety.start_yellow()
            for _ in range(YELLOW):                    # 3 s of yellow
                halting_total += self._sim_second()
            self.safety.finish_switch()
            seconds_left -= YELLOW
        for _ in range(seconds_left):
            halting_total += self._sim_second()
        self.safety.time_in_green += seconds_left
        self.t += DECISION_INTERVAL

        mean_halting = halting_total / DECISION_INTERVAL
        reward = -mean_halting / 10.0 - (SWITCH_PENALTY if switched else 0.0)
        truncated = self.t >= SIM_SECONDS               # one simulated hour = one episode
        return self._observe(), reward, False, truncated, {"switched": switched}

    def close(self):
        self._close()