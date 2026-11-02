"""Pure, explainable knowledge tracing. All times are UTC epoch seconds."""
from dataclasses import dataclass, asdict, field
import math
from .settings import CONFIG

@dataclass
class Parameters:
    prior: float = .35
    learn: float = .12
    slip: float = .1
    guess: float = .2
    half_life_days: float = 30

@dataclass
class State:
    mastery: float = .35
    attempts: int = 0
    errors: list = field(default_factory=list)
    response_ms: int = 0
    hints: int = 0
    last_practiced: float | None = None

P = Parameters(**CONFIG["bkt"])

def decayed(s, now, p=P):
    days = max(0, now - s.last_practiced) / 86400 if s.last_practiced is not None else 0
    return s.mastery * 2 ** (-days / p.half_life_days)

def predict(s, now, difficulty=0., p=P):
    m = decayed(s, now, p)
    base = m*(1-p.slip)+(1-m)*p.guess
    return 1/(1+math.exp(-(math.log(base/(1-base))-difficulty)))

def update(s, correct, now, error=None, response_ms=0, hints=0, retries=0, p=P):
    m = decayed(s, now, p)
    # Assisted/retried evidence is deliberately less diagnostic, not multiple independent trials.
    reliability = 1/(1+hints+retries)
    a,b = ((1-p.slip,p.guess) if correct else (p.slip,1-p.guess))
    a,b = a**reliability,b**reliability
    posterior = m*a / (m*a+(1-m)*b)
    mastery = posterior+(1-posterior)*p.learn
    errors = (s.errors+([{'type':error,'at':now}] if error else []))[-10:]
    return State(mastery,s.attempts+1,errors,response_ms,hints,now)

def project(s, sessions, now, p=P):
    # Expected learning transitions only. Not a causal estimate of real learning.
    m = decayed(s,now,p)
    return 1-(1-m)*(1-p.learn)**sessions
