"""LLM Harbour Master with an output validator and model-based fallback."""
import re

from .llm_client import SYSTEM_PROMPT

ALLOWED = {"warn_storm", "hold_ship"}
ACTION_RE = re.compile(r"^(warn_storm)\(\)$|^(hold_ship)\((\d+)\)$")


def validate(raw, waiting_ids):
    """Return (action, reason). action is (name, arg) or None if rejected.

    Strict rules: the whole reply must be exactly one allowed action; extra prose,
    several actions, unknown functions or ship IDs that are not waiting are rejected."""
    if raw is None:
        return None, "empty reply"
    text = raw.strip().strip("`").strip()
    if not text:
        return None, "empty reply"
    m = ACTION_RE.match(text)
    if not m:
        name = re.match(r"^\s*([A-Za-z_]+)\s*\(", text)
        if name and name.group(1) not in ALLOWED:
            return None, f"action '{name.group(1)}' not on allowed list"
        return None, "not exactly one allowed action"
    if m.group(1):
        return ("warn_storm", None), "ok"
    sid = int(m.group(3))
    if sid not in waiting_ids:
        return None, f"ship {sid} is not in the waiting list"
    return ("hold_ship", sid), "ok"


class HarbourMaster:
    def __init__(self, llm):
        self.llm = llm
        self.rejections = []

    def decide(self, h):
        report = h.text_report()
        raw = self.llm.complete(SYSTEM_PROMPT, report)
        h.stats.llm_calls += 1
        action, reason = validate(raw, h.waiting_ids())
        if action is None:
            h.stats.invalid_llm += 1
            h.stats.fallbacks += 1
            self.rejections.append((h.tick, raw, reason))
            fb = h.model_based_fallback()
            note = h.execute(fb, "fallback") if fb else "fallback: no action needed"
            h.stats.log.append(f"t={h.tick} REJECTED {raw!r} ({reason}) -> {note}")
            return
        h.stats.log.append(f"t={h.tick} " + h.execute(action, "LLM"))
