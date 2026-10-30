"""Lookout, Quartermaster and Dockworker agents."""
from . import config as C


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Lookout:
    """Simple reflex agent: sensor = the sky (storm schedule), actuator = broadcast."""

    def __init__(self, storms):
        self.storms = storms

    def broadcast(self, t):
        for s, e in self.storms:
            if t == s - C.WARNING_LEAD:
                return (s, e)
        return None

    def current_warning(self, t):
        """Warning that has been issued and is still relevant (warned or active)."""
        for s, e in self.storms:
            if s - C.WARNING_LEAD <= t < e:
                return (s, e)
        return None


class Quartermaster:
    """Assigns idle workers to berths: most unclaimed cargo first, nearest on ties."""

    def __init__(self, harbour):
        self.h = harbour

    def assign(self, worker, allowed):
        best, best_key = None, None
        for b in allowed:
            s = self.h.ship_at(b)
            if s is None or s.cargo <= 0:
                continue
            claimed = sum(1 for w in self.h.workers if w.target == b and w is not worker)
            key = (s.cargo - claimed, -manhattan(worker.pos, C.BERTHS[b]))
            if best_key is None or key > best_key:
                best, best_key = b, key
        return best


class Dockworker:
    """policy 'baseline': simple reflex with a fixed rule - go to the assigned berth,
    take one unit, carry it to the warehouse, repeat. Ignores storm warnings.

    policy 'model' / 'hm': model-based reflex agent. Keeps an internal model of
    known storm windows (from the Lookout, or relayed by the Harbour Master) and
    uses it to avoid B1/B4 when it would be there during a storm."""

    def __init__(self, wid, start, policy):
        self.wid = wid
        self.pos = start
        self.policy = policy
        self.carrying = False
        self.target = None
        self.stunned_until = -1
        self.known_storms = set()       # internal state (memory)

    # ----- memory -----
    def remember_storm(self, window):
        self.known_storms.add(window)

    def uses_memory(self):
        return self.policy in ("model", "hm")

    def is_stunned(self, t):
        return t < self.stunned_until

    def knock_out(self, t, h):
        h.stats.knockouts += 1
        if self.carrying:
            h.stats.cargo_lost += 1
            self.carrying = False
        self.target = None
        self.stunned_until = t + C.KNOCKOUT_TICKS

    # ----- model-based reasoning -----
    def _storm_overlaps(self, t0, t1):
        """Does any remembered storm overlap the tick interval [t0, t1]?"""
        return any(t0 < e and t1 >= s for s, e in self.known_storms)

    def berth_risky(self, berth, t):
        if berth not in C.UNSAFE_BERTHS or not self.uses_memory():
            return False
        bx, by = C.BERTHS[berth]
        # when would I enter the zone, and when would I be clear of it again?
        dist = manhattan(self.pos, (bx, by))
        enter = t + max(0, dist - C.UNSAFE_DEPTH - C.UNSAFE_RADIUS_X)
        leave = t + dist + 1 + C.UNSAFE_DEPTH + 1      # walk + pick up + walk out
        return self._storm_overlaps(enter, leave)

    def _danger_imminent_here(self, t):
        from .world import in_danger_zone
        if not self.uses_memory() or not in_danger_zone(self.pos):
            return False
        escape = C.UNSAFE_DEPTH + 1 - self.pos[1]
        return self._storm_overlaps(t, t + escape + 1)

    # ----- movement -----
    def _step_towards(self, goal, vertical_first):
        x, y = self.pos
        gx, gy = goal
        if vertical_first and y != gy:
            y += 1 if gy > y else -1
        elif x != gx:
            x += 1 if gx > x else -1
        elif y != gy:
            y += 1 if gy > y else -1
        self.pos = (x, y)

    # ----- one tick -----
    def act(self, h):
        t = h.tick
        if self.is_stunned(t):
            return
        # Model-based: if a remembered storm is about to hit my cell, get out (south).
        if self._danger_imminent_here(t):
            self.target = None if not self.carrying else self.target
            self.pos = (self.pos[0], self.pos[1] + 1)
            return

        if self.carrying:
            if self.pos == C.WAREHOUSE:
                self.carrying = False
                h.deliver()
            else:
                self._step_towards(C.WAREHOUSE, vertical_first=True)  # leave berths quickly
            return

        # Need a berth with cargo.
        if self.target is not None:
            s = h.ship_at(self.target)
            if s is None or s.cargo <= 0 or self.berth_risky(self.target, t):
                self.target = None
        if self.target is None:
            allowed = [b for b in C.BERTHS if not self.berth_risky(b, t)]
            self.target = h.qm.assign(self, allowed)
        if self.target is None:
            # nothing safe to do: wait, stepping out of any danger zone row
            if self.uses_memory() and self.pos[1] <= C.UNSAFE_DEPTH:
                self.pos = (self.pos[0], self.pos[1] + 1)
            return

        goal = C.BERTHS[self.target]
        if self.pos == goal:
            if h.pickup(self.target):
                self.carrying = True
            self.target = None
        else:
            # travel along the lower rows first, approach the berth last
            self._step_towards(goal, vertical_first=False)
