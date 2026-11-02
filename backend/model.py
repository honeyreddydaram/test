"""Pure, explainable knowledge tracing. All times are UTC epoch seconds."""

import math
from dataclasses import dataclass, field

from .settings import CONFIG


@dataclass
class Parameters:
    prior: float = 0.35
    learn: float = 0.12
    slip: float = 0.1
    guess: float = 0.2
    half_life_days: float = 30


P = Parameters(**CONFIG["bkt"])


@dataclass
class State:
    mastery: float = P.prior
    attempts: int = 0
    errors: list = field(default_factory=list)
    response_ms: int = 0
    hints: int = 0
    last_practiced: float | None = None


def decayed(state: State, now: float, p=P) -> float:
    elapsed_days = (
        max(0, now - state.last_practiced) / 86400
        if state.last_practiced is not None
        else 0
    )
    return state.mastery * 2 ** (-elapsed_days / p.half_life_days)


def predict(state: State, now: float, difficulty=0.0, p=P) -> float:
    mastery = decayed(state, now, p)
    base_success = mastery * (1 - p.slip) + (1 - mastery) * p.guess
    log_odds = math.log(base_success / (1 - base_success)) - difficulty
    return 1 / (1 + math.exp(-log_odds))


def update(
    state: State,
    correct: bool,
    now: float,
    error=None,
    response_ms=0,
    hints=0,
    retries=0,
    p=P,
    evidence_weight=1.0,
) -> State:
    mastery = decayed(state, now, p)
    # Hints/retries weaken diagnosis. Repeat exposure also weakens learning gain.
    reliability = evidence_weight / (1 + hints + retries)
    if correct:
        known_likelihood, unknown_likelihood = 1 - p.slip, p.guess
    else:
        known_likelihood, unknown_likelihood = p.slip, 1 - p.guess

    known_likelihood **= reliability
    unknown_likelihood **= reliability
    posterior = (
        mastery
        * known_likelihood
        / (mastery * known_likelihood + (1 - mastery) * unknown_likelihood)
    )
    next_mastery = posterior + (1 - posterior) * p.learn * evidence_weight
    recent_errors = state.errors + ([{"type": error, "at": now}] if error else [])
    return State(
        mastery=next_mastery,
        attempts=state.attempts + 1,
        errors=recent_errors[-10:],
        response_ms=response_ms,
        hints=hints,
        last_practiced=now,
    )


def project(state: State, sessions: int, now: float, p=P) -> float:
    # Expected transitions for fresh practice, not a causal estimate of real learning.
    mastery = decayed(state, now, p)
    return 1 - (1 - mastery) * (1 - p.learn) ** sessions
