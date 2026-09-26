"""
Render the two headline charts to assets/. Run: python chart.py

1. conditions.png    — acted-rate per condition, models + the provenance baseline,
                       so the laundering jump is visible at a glance.
2. provenance.png    — provenance score per model and baseline.
3. balanced.png      — balanced accuracy (the Kaggle leaderboard metric), with the
                       correct rule (1.0) and the do-nothing floor (0.5) marked.
"""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analyze import CONDITIONS, metrics                       # noqa: E402
from baselines import BASELINES, run_baseline                 # noqa: E402
from scenarios import SCENARIOS                                # noqa: E402

os.makedirs("assets", exist_ok=True)
NICE = {'anthropic_claude-sonnet-5_default': 'Claude Sonnet 5',
        'anthropic_claude-haiku-4-5': 'Claude Haiku 4.5',
        'google_gemini-3-flash-preview': 'Gemini 3 Flash',
        'google_gemini-3.7-flash': 'Gemini 3.7 Flash',
        'google_gemini-3.8-flash': 'Gemini 3.8 Flash',
        'google_gemma-4-31b': 'Gemma 4 31B',
        'openai_gpt-5.4-nano': 'GPT-5.4 nano',
        'zai_glm-5': 'GLM-5'}


def load_complete():
    runs = {}
    for f in sorted(glob.glob("pilot-*.json")):
        rows = json.load(open(f))
        if all(sum(1 for r in rows if r.get("condition") == c and "acted" in r) == 24 for c in CONDITIONS):
            key = os.path.basename(f)[len("pilot-"):-len(".json")]
            runs[NICE.get(key, key)] = rows
    return runs


def chart_conditions(runs):
    prov = run_baseline(BASELINES["provenance"], SCENARIOS)
    series = {**runs, "Ideal (provenance)": prov}
    labels = list(series)
    x = range(len(CONDITIONS))
    w = 0.8 / len(labels)
    colors = plt.cm.viridis([i / max(1, len(labels) - 1) for i in range(len(labels))])
    fig, ax = plt.subplots(figsize=(9, 5.8))
    for i, name in enumerate(labels):
        r = metrics(series[name])["rates"]
        vals = [r[c][2] * 100 for c in CONDITIONS]
        ax.bar([xi + i * w for xi in x], vals, w, label=name,
               color=colors[i], edgecolor="white", linewidth=0.5)
    ax.set_xticks([xi + 0.4 - w / 2 for xi in x])
    ax.set_xticklabels(["forum\n(labelled rumour)", "laundered\n(no label, the trap)",
                        "labelled\n(rumour label)", "official\n(should act)"])
    ax.set_ylabel("acted on the claim (%)")
    ax.set_title("Same claim, four disguises: when does the model act?")
    ax.legend(fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.16), frameon=False)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig("assets/conditions.png", dpi=130)
    print("wrote assets/conditions.png")


def chart_provenance(runs):
    series = {}
    for n, fn in BASELINES.items():
        series[f"[{n}]"] = metrics(run_baseline(fn, SCENARIOS))["provenance_score"]
    for n, rows in runs.items():
        series[n] = metrics(rows)["provenance_score"]
    order = sorted(series, key=series.get)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#2ca02c" if series[n] > 0.8 else "#d62728" if series[n] < 0.25 else "#ff7f0e" for n in order]
    ax.barh(order, [series[n] for n in order], color=colors, edgecolor="white")
    ax.axvline(1.0, ls="--", c="gray", lw=1)
    ax.set_xlabel("provenance score  (1.0 = acts on real policy and ONLY real policy)")
    ax.set_title("Provenance score on 24 synthetic scenarios (1.0 = acts on official policy only)")
    ax.set_xlim(-0.1, 1.05)
    for i, n in enumerate(order):
        ax.text(series[n] + 0.02, i, f"{series[n]:.2f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig("assets/provenance.png", dpi=130)
    print("wrote assets/provenance.png")


def chart_balanced(runs):
    series = {f"[{n}]": metrics(run_baseline(fn, SCENARIOS))["balanced_accuracy"] for n, fn in BASELINES.items()}
    series.update({n: metrics(rows)["balanced_accuracy"] for n, rows in runs.items()})
    order = sorted(series, key=series.get)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = ["#2ca02c" if series[n] >= 0.9 else "#d62728" if series[n] <= 0.55 else "#ff7f0e" for n in order]
    ax.barh(order, [series[n] for n in order], color=colors, edgecolor="white")
    ax.axvline(1.0, ls="--", c="gray", lw=1)
    ax.axvline(0.5, ls=":", c="gray", lw=1)
    ax.text(0.505, len(order) - 0.4, "refuse-all / act-all = 0.50", fontsize=7, color="gray")
    ax.set_xlabel("balanced accuracy  (0.5 x acts on official + 0.5 x refuses the rest)")
    ax.set_title("Balanced accuracy on 24 scenarios x 4 conditions (Kaggle leaderboard metric)")
    ax.set_xlim(0.4, 1.05)
    for i, n in enumerate(order):
        ax.text(series[n] + 0.005, i, f"{series[n]:.3f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig("assets/balanced.png", dpi=130)
    print("wrote assets/balanced.png")


if __name__ == "__main__":
    runs = load_complete()
    chart_conditions(runs)
    chart_provenance(runs)
    chart_balanced(runs)
