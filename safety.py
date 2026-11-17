"""Phase 3 - Deterministic safety logic for the traffic light.

PPO only *suggests* a phase. This class decides what actually happens:
  - MIN_GREEN: a green phase cannot be cut before 10 s.
  - YELLOW:    a 3 s yellow is always inserted when switching.
  - MAX_GREEN: after 60 s of green the light is forced to switch (no road starves).

Phase indices in our SUMO program: 0 = NS green, 1 = NS yellow,
                                   2 = EW green, 3 = EW yellow.
"""
import traci

TL_ID = "C"
MIN_GREEN = 10
YELLOW = 3
MAX_GREEN = 60
NS, EW = 0, 1                       # PPO actions / logical phases
GREEN_INDEX = {NS: 0, EW: 2}        # SUMO phase index of each green
YELLOW_INDEX = {NS: 1, EW: 3}       # yellow shown when leaving that green
HOLD = 100000                       # keep a phase "forever" (we switch it manually)


class SignalSafety:
    def __init__(self):
        self.current = NS
        self.time_in_green = 0

    def reset(self):
        self.current = NS
        self.time_in_green = 0
        self._set_green(NS)

    def _set_green(self, phase):
        traci.trafficlight.setPhase(TL_ID, GREEN_INDEX[phase])
        traci.trafficlight.setPhaseDuration(TL_ID, HOLD)

    def decide(self, requested):
        """Return True if the light must switch now, given PPO's request."""
        if self.time_in_green >= MAX_GREEN:
            return True                                   # forced switch
        if requested != self.current and self.time_in_green >= MIN_GREEN:
            return True                                   # allowed switch
        return False                                      # request ignored

    def start_yellow(self):
        traci.trafficlight.setPhase(TL_ID, YELLOW_INDEX[self.current])
        traci.trafficlight.setPhaseDuration(TL_ID, HOLD)

    def finish_switch(self):
        self.current = EW if self.current == NS else NS
        self._set_green(self.current)
        self.time_in_green = 0