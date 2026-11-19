"""Phase 2/3 - Collects traffic metrics from a running SUMO simulation via TraCI.

Call collector.update() after every traci.simulationStep(); call
collector.summary() at the end to get one dictionary of results.

Metrics:
  avg_wait_s         average time a vehicle spent stopped (speed < 0.1 m/s)
  avg_time_loss_s    average extra travel time versus driving freely (no speed threshold,
                     so it cannot be 'gamed' by cars that crawl instead of stopping)
  avg_queue/max_queue  stopped vehicles per approach road
  stops_per_vehicle  how many times a vehicle went from moving to stopped
  throughput         vehicles that finished their trip
  unfinished         vehicles still in the network at the end of the hour
  pending_end        vehicles that could NOT enter the network (entrance jammed) at the end.
                     They are invisible to the other waiting metrics, so always read
                     avg_wait together with pending_end and served_pct.
  served_pct         share of all vehicles (entered + pending) that finished their trip
"""
import traci
import traci.constants as tc
from config import APPROACHES

STOP_SPEED = 0.1  # m/s: below this a vehicle counts as stopped
VARS = [tc.VAR_SPEED, tc.VAR_ACCUMULATED_WAITING_TIME, tc.VAR_TIMELOSS]


class MetricsCollector:
    def __init__(self):
        self.step_count = 0
        self.queue_sum = {a: 0 for a in APPROACHES}
        self.queue_max = {a: 0 for a in APPROACHES}
        self.waiting = {}      # vehicle id -> latest accumulated waiting time (s)
        self.time_loss = {}    # vehicle id -> latest cumulative time loss (s)
        self.stopped = {}      # vehicle id -> was it stopped at the previous step?
        self.stops = 0
        self.arrived = 0
        self.entered = set()
        self.pending = 0

    def update(self):
        self.step_count += 1
        for a in APPROACHES:
            q = traci.edge.getLastStepHaltingNumber(f"{a}2C")
            self.queue_sum[a] += q
            self.queue_max[a] = max(self.queue_max[a], q)
        # One subscription per vehicle: SUMO sends all values in a single message per
        # step, which is much faster than asking vehicle by vehicle.
        for vid in traci.simulation.getDepartedIDList():
            traci.vehicle.subscribe(vid, VARS)
        for vid, data in traci.vehicle.getAllSubscriptionResults().items():
            self.entered.add(vid)
            self.waiting[vid] = data[tc.VAR_ACCUMULATED_WAITING_TIME]
            self.time_loss[vid] = data[tc.VAR_TIMELOSS]
            is_stopped = data[tc.VAR_SPEED] < STOP_SPEED
            if is_stopped and not self.stopped.get(vid, False):
                self.stops += 1
            self.stopped[vid] = is_stopped
        self.arrived += traci.simulation.getArrivedNumber()
        self.pending = len(traci.simulation.getPendingVehicles())

    def summary(self):
        n = max(len(self.entered), 1)
        res = {
            "vehicles_entered": len(self.entered),
            "throughput": self.arrived,
            "unfinished": len(self.entered) - self.arrived,
            "pending_end": self.pending,
            "served_pct": round(100 * self.arrived / max(len(self.entered) + self.pending, 1), 1),
            "avg_wait_s": round(sum(self.waiting.values()) / n, 2),
            "avg_time_loss_s": round(sum(self.time_loss.values()) / n, 2),
            "stops_per_vehicle": round(self.stops / n, 2),
            "avg_queue": round(sum(self.queue_sum.values()) / (4 * self.step_count), 2),
            "max_queue": max(self.queue_max.values()),
        }
        for a in APPROACHES:
            res[f"avg_queue_{a}"] = round(self.queue_sum[a] / self.step_count, 2)
        return res