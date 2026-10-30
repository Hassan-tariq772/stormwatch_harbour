"""Stormwatch Harbour - run every experiment for CGD-460 Assignment 2.

Usage:
    python run.py                 # mock LLM, seeds 11-13 (+ extra 11-15 table)
    python run.py --llm real      # real OpenAI-compatible LLM (needs LLM_API_KEY)
    python run.py --seeds 11 12   # custom seeds
Outputs go to results/.
"""
import argparse
import csv
import os
from statistics import mean

from sim import config as C
from sim.world import Harbour
from sim.harbour_master import HarbourMaster
from sim.llm_client import MockLLM, RealLLM
from sim import safety

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FIELDS = ["policy", "seed", "cargo_delivered", "knockouts", "cargo_lost",
          "ships_arrived", "ships_completed", "llm_calls", "invalid_llm", "fallbacks", "holds"]
LABEL = {"baseline": "Baseline (fixed rule)", "model": "Model-based",
         "hm": "LLM Harbour Master + fallback"}


def make_llm(kind, seed, **kw):
    return RealLLM() if kind == "real" else MockLLM(seed, **kw)


def run_one(policy, seed, llm_kind="mock", **llm_kw):
    hm = HarbourMaster(make_llm(llm_kind, seed, **llm_kw)) if policy == "hm" else None
    h = Harbour(seed, policy, hm)
    return h.run(), h


def experiment(seeds, llm_kind):
    rows, logs = [], []
    for policy in ("baseline", "model", "hm"):
        for seed in seeds:
            st, h = run_one(policy, seed, llm_kind)
            rows.append({k: getattr(st, k) for k in FIELDS})
            if policy == "hm":
                logs.append(f"--- seed {seed} storms={h.storms} ---")
                logs.extend(st.log)
    return rows, logs


def averages(rows):
    out = {}
    for p in ("baseline", "model", "hm"):
        r = [x for x in rows if x["policy"] == p]
        out[p] = {k: mean(x[k] for x in r) for k in FIELDS[2:]}
    return out


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def md_table(rows, avg, seeds):
    lines = ["| Policy | " + " | ".join(f"Seed {s}" for s in seeds) + " | Average |",
             "|---|" + "---|" * (len(seeds) + 1)]
    for p in ("baseline", "model", "hm"):
        cells = []
        for s in seeds:
            r = next(x for x in rows if x["policy"] == p and x["seed"] == s)
            cells.append(f"{r['cargo_delivered']} / {r['knockouts']}")
        a = avg[p]
        lines.append(f"| {LABEL[p]} | " + " | ".join(cells) +
                     f" | {a['cargo_delivered']:.1f} / {a['knockouts']:.1f} |")
    lines.append("\nCells show *cargo delivered / storm knock-outs*.")
    return "\n".join(lines)


def chart(avg, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pols = ["baseline", "model", "hm"]
    names = ["Baseline", "Model-based", "LLM HM"]
    colors = ["#9aa5b1", "#2f6db5", "#e08a2c"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2))
    for ax, key, title in ((axes[0], "cargo_delivered", "Cargo delivered (avg, seeds 11-13)"),
                           (axes[1], "knockouts", "Storm knock-outs (avg, seeds 11-13)")):
        vals = [avg[p][key] for p in pols]
        bars = ax.bar(names, vals, color=colors, width=0.6)
        ax.set_title(title, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, max(vals) * 1.18 + 0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", choices=["mock", "real"], default="mock")
    ap.add_argument("--seeds", type=int, nargs="+", default=C.MAIN_SEEDS)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    rows, logs = experiment(args.seeds, args.llm)
    avg = averages(rows)
    write_csv(os.path.join(OUT, "runs.csv"), rows, FIELDS)
    with open(os.path.join(OUT, "hm_decision_log.txt"), "w") as f:
        f.write("\n".join(logs))
    chart(avg, os.path.join(OUT, "chart.png"))

    extra_rows, _ = experiment(C.EXTRA_SEEDS, args.llm)
    extra_avg = averages(extra_rows)
    write_csv(os.path.join(OUT, "runs_seeds_11_15.csv"), extra_rows, FIELDS)

    # Limitation test (mock only): an LLM whose replies are always well-formed but
    # which always picks hold_ship() instead of warn_storm() when a storm is coming.
    # The validator cannot catch this, because every reply is on the allowed list.
    stress = []  # limitation-test rows
    for seed in args.seeds:
        st, _ = run_one("hm", seed, "mock", error_rate=0.0, wrong_rate=1.0)
        stress.append({k: getattr(st, k) for k in FIELDS})
    write_csv(os.path.join(OUT, "limitation_test.csv"), stress, FIELDS)

    safety_rows = []
    for mode, llm in (("normal", make_llm(args.llm, 11, error_rate=0, wrong_rate=0)),
                      ("naive/worst-case", MockLLM(11, naive=True))):
        for r in safety.run_all(llm):
            r["llm_mode"] = mode
            safety_rows.append(r)
    write_csv(os.path.join(OUT, "safety_results.csv"), safety_rows,
              ["llm_mode", "case", "llm_output", "validator", "system_result", "passed"])

    md = [f"# Results (LLM backend: {args.llm})", "", "## Seeds " + ", ".join(map(str, args.seeds)),
          md_table(rows, avg, args.seeds), "",
          "## LLM Harbour Master details", "| Seed | Cargo | LLM calls | Invalid outputs | Fallback uses |",
          "|---|---|---|---|---|"]
    for r in rows:
        if r["policy"] == "hm":
            md.append(f"| {r['seed']} | {r['cargo_delivered']} | {r['llm_calls']} | "
                      f"{r['invalid_llm']} | {r['fallbacks']} |")
    md += ["", "## Limitation test: valid-but-wrong LLM (never warns, always well-formed)",
           "| Seed | Cargo | Knock-outs | Invalid outputs | Fallback uses |", "|---|---|---|---|---|"]
    for r in stress:
        md.append(f"| {r['seed']} | {r['cargo_delivered']} | {r['knockouts']} | "
                  f"{r['invalid_llm']} | {r['fallbacks']} |")
    md += ["", "## Extra: seeds 11-15", md_table(extra_rows, extra_avg, C.EXTRA_SEEDS), "",
           "## Safety cases", "| LLM mode | Case | LLM output | Validator | System result | Pass |",
           "|---|---|---|---|---|---|"]
    for r in safety_rows:
        md.append(f"| {r['llm_mode']} | {r['case']} | `{r['llm_output']}` | {r['validator']} | "
                  f"{r['system_result']} | {'PASS' if r['passed'] else 'FAIL'} |")
    with open(os.path.join(OUT, "summary.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
