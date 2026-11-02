"""Seeded synthetic benchmark with latent skills, paired policies, and no real learners."""

import json
import random
from pathlib import Path
from .model import State, Parameters, predict, update
from .engine import ITEMS, SKILLS, recommend


def metrics(predictions, labels):
    n = len(labels)
    # Pairwise rank AUC via tie-aware rank sums, O(n log n).
    pairs = sorted(zip(predictions, labels))
    rank_sum = 0.0
    i = 0
    while i < n:
        j = i + 1
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        rank_sum += sum(y for _, y in pairs[i:j]) * ((i + 1 + j) / 2)
        i = j
    pos = sum(labels)
    neg = n - pos
    auc = (rank_sum - pos * (pos + 1) / 2) / (pos * neg) if pos and neg else None
    bins = []
    for b in range(10):
        selected = [
            (p, y) for p, y in zip(predictions, labels) if min(int(p * 10), 9) == b
        ]
        if selected:
            bins.append(
                {
                    "bin": b,
                    "count": len(selected),
                    "predicted": sum(p for p, _ in selected) / len(selected),
                    "observed": sum(y for _, y in selected) / len(selected),
                }
            )
    return {
        "n": n,
        "auc": auc,
        "accuracy": sum((p >= 0.5) == y for p, y in zip(predictions, labels)) / n,
        "brier": sum((p - y) ** 2 for p, y in zip(predictions, labels)) / n,
        "ece": sum(b["count"] * abs(b["predicted"] - b["observed"]) for b in bins) / n,
        "calibration_bins": bins,
    }


def run(seed=20261102, learners=100, steps=200):
    policies = {}
    by_skill = {
        k: [i for i in ITEMS if i["skill"] == k and i["type"] != "writing"]
        for k in SKILLS
    }
    # Interleave concepts; bank ordering must not give fixed practice blocks of one skill.
    bank = [
        by_skill[k][n]
        for n in range(max(map(len, by_skill.values())))
        for k in SKILLS
        if n < len(by_skill[k])
    ]
    for mode in ("adaptive", "hard_prerequisites", "fixed"):
        predictions = []
        labels = []
        counts = []
        reached = []
        final = []
        for person in range(learners):
            # Counterfactual draws indexed by learner, skill and exposure, rather than call order.
            rng = random.Random(seed + person)
            learn = rng.uniform(0.06, 0.18)
            slip = rng.uniform(0.05, 0.15)
            guess = rng.uniform(0.1, 0.3)
            truth = {k: rng.random() < 0.35 for k in SKILLS}
            state = {}
            exposures = {k: 0 for k in SKILLS}
            previous = None
            hit = None
            item_counts = {}
            for t in range(steps):
                now = 1700000000 + t * 300
                item, _, _ = (
                    recommend(
                        state,
                        now,
                        previous,
                        item_counts,
                        prerequisite_mode=(
                            "hard" if mode == "hard_prerequisites" else "soft"
                        ),
                    )
                    if mode != "fixed"
                    else (bank[t % len(bank)], 0, "fixed")
                )
                k = item["skill"]
                exposures[k] += 1
                draw = random.Random(f"{seed}:{person}:{k}:{exposures[k]}")
                outcome = draw.random() < ((1 - slip) if truth[k] else guess)
                predictions.append(predict(state.get(k, State()), now))
                labels.append(int(outcome))
                repeats = item_counts.get(item["id"], 0)
                state[k] = update(
                    state.get(k, State()),
                    outcome,
                    now,
                    evidence_weight=1 / (1 + repeats),
                )
                item_counts[item["id"]] = repeats + 1
                if not truth[k] and draw.random() < learn:
                    truth[k] = True
                previous = item["id"]
                if hit is None and sum(truth.values()) / len(truth) >= 0.85:
                    hit = t + 1
            reached.append(hit is not None)
            counts.append(hit if hit is not None else steps)
            final.append(sum(truth.values()) / len(truth))
        policies[mode] = {
            "prediction": metrics(predictions, labels),
            "fraction_reaching_85_percent_latent_skills": sum(reached) / learners,
            "restricted_mean_steps_to_85_percent": sum(counts) / learners,
            "mean_final_latent_mastery": sum(final) / learners,
        }
    return {
        "seed": seed,
        "learners": learners,
        "steps_per_learner": steps,
        "assumptions": "Heterogeneous learn/slip/guess; binary latent skills; no latent prerequisite effects or forgetting during a short run; censored at budget; BKT defaults intentionally imperfect. Paired skill-exposure random draws. All policies use the same 90-item bank and repeat-evidence weighting. No item memorization in the latent simulator; extra items alone cannot improve its true learning. No claim about child learning.",
        "policies": policies,
    }


if __name__ == "__main__":
    output = run()
    path = Path(__file__).resolve().parents[1] / "reports/simulation.json"
    path.write_text(json.dumps(output, indent=2))
    print(
        json.dumps(
            {
                k: {key: v for key, v in val.items() if key != "prediction"}
                for k, val in output["policies"].items()
            },
            indent=2,
        )
    )
