"""Deterministic grading and explainable selection over a curated item bank."""

import json
import re
from pathlib import Path

from .model import State, decayed, predict
from .settings import CONFIG

LOW, HIGH = CONFIG["policy"]["target_success"]
TARGET = (LOW + HIGH) / 2
READY = CONFIG["policy"]["prerequisite_mastery"]
SOFT_WEIGHT = CONFIG["policy"]["prerequisite_penalty"]
ROOT = Path(__file__).resolve().parents[1]
GRAPH = json.loads((ROOT / "data/skills.json").read_text())
SKILLS = {skill["id"]: skill for skill in GRAPH["skills"]}
ITEMS = json.loads((ROOT / "data/exercises.json").read_text())
ITEM_MAP = {item["id"]: item for item in ITEMS}


def normalize(text):
    """Ignore presentation differences, without accepting arbitrary substrings."""
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".!?")


def check(item, answer):
    if item["type"] == "writing":
        return {
            "correct": None,
            "error": None,
            "feedback": "Writing is an unscored activity. These checks cannot reliably judge unrestricted English.",
        }

    text = normalize(answer)
    correct = text in {normalize(value) for value in item["answers"]}
    distractors = {normalize(key): value for key, value in item["distractors"].items()}
    error = None if correct else distractors.get(text, "unclassified")
    skill = SKILLS[item["skill"]]
    if correct:
        feedback = "Correct. " + skill["rule"]
    else:
        feedback = next(
            (entry["feedback"] for entry in skill["errors"] if entry["id"] == error),
            "That answer does not match the curated key. " + skill["rule"],
        )
    return {"correct": correct, "error": error, "feedback": feedback}


def foundation_gap(skill_id, states, now):
    """A bounded teaching preference, never a lock on a skill."""
    prerequisites = SKILLS[skill_id]["prerequisites"]
    if not prerequisites:
        return 0.0
    deficits = [
        max(0.0, READY - decayed(states.get(key, State()), now)) / READY
        for key in prerequisites
    ]
    return sum(deficits) / len(deficits)


def recommend(states, now, previous=None, item_counts=None, prerequisite_mode="soft"):
    """Choose a skill first, then rotate its least-exposed items.

    Soft prerequisites contribute to ranking rather than eligibility. In the
    fallback, coverage takes priority; otherwise new skills could stay untouched.
    Item counts are persistent per learner and include issued (even skipped) items.
    """
    item_counts = item_counts or {}
    by_skill = {}
    for item in ITEMS:
        if item["type"] != "writing":
            by_skill.setdefault(item["skill"], []).append(item)

    candidates = []
    for skill_id, bank in by_skill.items():
        if prerequisite_mode == "hard" and foundation_gap(skill_id, states, now) > 0:
            continue
        # Within a skill, an unseen item always precedes a repeated one.
        item = min(
            bank,
            key=lambda value: (
                item_counts.get(value["id"], 0),
                value["id"] == previous,
                value["id"],
            ),
        )
        probability = predict(states.get(skill_id, State()), now, item["difficulty"])
        gap = foundation_gap(skill_id, states, now)
        score = abs(probability - TARGET) + SOFT_WEIGHT * gap
        candidates.append((score, item, probability, gap))

    in_zone = [candidate for candidate in candidates if LOW <= candidate[2] <= HIGH]
    if in_zone:
        selected = min(in_zone, key=lambda value: (value[0], value[1]["id"]))
        strategy = "Within the target challenge zone."
    else:
        selected = min(
            candidates,
            key=lambda value: (
                states.get(value[1]["skill"], State()).attempts,
                value[0],
                value[1]["id"],
            ),
        )
        strategy = "No skill is in the target zone; explore a least-practiced skill."

    _, item, probability, gap = selected
    exposure = item_counts.get(item["id"], 0)
    reason = (
        f"Predicted success {probability:.0%}. {strategy} "
        f"Soft prerequisites add a {SOFT_WEIGHT * gap:.3f} ranking penalty; no skill is locked. "
        f"This item has been shown {exposure} times; less-exposed items come first within the skill."
    )
    return item, probability, reason


def public_item(item):
    return {
        key: value
        for key, value in item.items()
        if key not in ("answers", "distractors")
    }


def validate_generated(candidate):
    """Generated proposals cannot create their own grading authority."""
    for item in ITEMS:
        if all(
            candidate.get(key) == item[key]
            for key in ("skill", "type", "prompt", "options")
        ):
            return item.copy()
    raise ValueError(
        "Generated exercise requires independent review or a deterministic rule proof."
    )
