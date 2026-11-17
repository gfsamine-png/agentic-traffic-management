"""Phase 2 - Collects traffic metrics from a running SUMO simulation via TraCI.

Call collector.update() after every traci.simulationStep(); call
collector.summary() at the end to get one dictionary of results.
"""
import traci
from config import APPROACHES

STOP_SPEED = 0.1  # m/s: below this a vehicle counts as stopped


class MetricsCollector:
    def __init__(self):
        self.step_count = 0
        self.queue_sum = {a: 0 for a in APPROACHES}   # sum over time of halting cars
        self.queue_max = {a: 0 for a in APPROACHES}
        self.waiting = {}      # vehicle id -> latest accumulated waiting time (s)
        self.stopped = {}      # vehicle id -> was it stopped at the previous step?
        self.stops = 0         # number of times a vehicle went from moving to stopped
        self.arrived = 0       # vehicles that finished their trip
        self.entered = set()   # every vehicle that ever appeared

    def update(self):
        self.step_count += 1
        for a in APPROACHES:
            q = traci.edge.getLastStepHaltingNumber(f"{a}2C")
            self.queue_sum[a] += q
            self.queue_max[a] = max(self.queue_max[a], q)
        for vid in traci.vehicle.getIDList():
            self.entered.add(vid)
            # Cumulative waiting time (needs --waiting-time-memory 3600 at start)
            self.waiting[vid] = traci.vehicle.getAccumulatedWaitingTime(vid)
            is_stopped = traci.vehicle.getSpeed(vid) < STOP_SPEED
            if is_stopped and not self.stopped.get(vid, False):
                self.stops += 1
            self.stopped[vid] = is_stopped
        self.arrived += traci.simulation.getArrivedNumber()

    def summary(self):
        n = max(len(self.entered), 1)
        res = {
            "vehicles_entered": len(self.entered),
            "throughput": self.arrived,
            "avg_wait_s": round(sum(self.waiting.values()) / n, 2),
            "stops_per_vehicle": round(self.stops / n, 2),
            "avg_queue": round(sum(self.queue_sum.values()) / (4 * self.step_count), 2),
            "max_queue": max(self.queue_max.values()),
        }
        for a in APPROACHES:
            res[f"avg_queue_{a}"] = round(self.queue_sum[a] / self.step_count, 2)
        return res