"""Phase 3 - Train the PPO agent and save it to models/ppo_traffic.zip.

Usage:  python train_ppo.py [total_timesteps]      (default 150000)
"""
import sys
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from config import ROOT, RESULTS_DIR

MODELS_DIR = ROOT / "models"


def main():
    from gym_env import TrafficEnv
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 150_000
    MODELS_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    env = Monitor(TrafficEnv(), str(RESULTS_DIR / "train_monitor"))   # logs reward per episode
    model = PPO("MlpPolicy", env, n_steps=1440, batch_size=144, gamma=0.99,
                learning_rate=3e-4, ent_coef=0.01, seed=0, verbose=1)
    model.learn(total_timesteps=steps)
    model.save(str(MODELS_DIR / "ppo_traffic"))
    env.close()
    print("Saved model to", MODELS_DIR / "ppo_traffic.zip")


if __name__ == "__main__":
    main()