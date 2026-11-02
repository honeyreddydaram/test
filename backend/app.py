"""Local single-user research demo. Session tokens are bearer credentials."""

import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .model import State, decayed, update, project
from .engine import GRAPH, SKILLS, ITEM_MAP, recommend, check, public_item

DB = os.getenv("TWIN_DB", str(Path(__file__).resolve().parents[1] / "twin.sqlite"))
app = FastAPI(title="Grammar Garden — learner twin research demo")


@contextmanager
def db():
    conn = sqlite3.connect(DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS learners (token TEXT PRIMARY KEY, state TEXT NOT NULL)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS events (token TEXT, event TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS issued (id TEXT PRIMARY KEY, token TEXT, item TEXT, started REAL, hints INTEGER DEFAULT 0, used INTEGER DEFAULT 0)"
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def identity(authorization):
    token = (authorization or "").removeprefix("Bearer ")
    with db() as conn:
        row = conn.execute(
            "SELECT state FROM learners WHERE token=?", (token,)
        ).fetchone()
    if not row:
        raise HTTPException(401, "Create or resume a demo session.")
    return token, {k: State(**v) for k, v in json.loads(row[0]).items()}


@app.post("/api/session")
def session():
    token = secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute("INSERT INTO learners VALUES (?,?)", (token, "{}"))
    return {"token": token}


@app.get("/api/graph")
def graph():
    return GRAPH


@app.get("/api/state")
def state(authorization: str | None = Header(None)):
    token, states = identity(authorization)
    now = time.time()
    with db() as conn:
        events = [
            json.loads(r[0])
            for r in conn.execute(
                "SELECT event FROM events WHERE token=? ORDER BY rowid DESC LIMIT 20",
                (token,),
            )
        ]
    streak = 0
    for e in events:
        if e["correct"] is not True:
            break
        streak += 1
    return {
        "skills": {
            k: {
                **asdict(states.get(k, State())),
                "mastery": decayed(states.get(k, State()), now),
            }
            for k in SKILLS
        },
        "events": events,
        "streak": streak,
        "badges": sum(decayed(states.get(k, State()), now) >= 0.85 for k in SKILLS),
    }


@app.get("/api/next")
def next_item(authorization: str | None = Header(None), writing: bool = False):
    token, states = identity(authorization)
    with db() as conn:
        previous = conn.execute(
            "SELECT item FROM issued WHERE token=? AND used=1 ORDER BY started DESC LIMIT 1",
            (token,),
        ).fetchone()
        item_counts = dict(
            conn.execute(
                "SELECT item, COUNT(*) FROM issued WHERE token=? GROUP BY item",
                (token,),
            )
        )
        item, prob, reason = recommend(
            states, time.time(), previous[0] if previous else None, item_counts
        )
        if writing:
            item = ITEM_MAP["writing-1"]
            prob = None
            reason = "Optional unscored writing; no mastery update."
        iid = secrets.token_urlsafe(16)
        conn.execute(
            "INSERT INTO issued(id,token,item,started) VALUES(?,?,?,?)",
            (iid, token, item["id"], time.time()),
        )
    return {
        "exercise": public_item(item),
        "attempt_id": iid,
        "predicted_success": prob,
        "reason": reason,
    }


class Hint(BaseModel):
    attempt_id: str = Field(max_length=100)


@app.post("/api/hint")
def hint(body: Hint, authorization: str | None = Header(None)):
    token, _ = identity(authorization)
    with db() as conn:
        row = conn.execute(
            "SELECT item FROM issued WHERE id=? AND token=? AND used=0",
            (body.attempt_id, token),
        ).fetchone()
        if not row:
            raise HTTPException(409, "Exercise expired or already answered.")
        conn.execute("UPDATE issued SET hints=hints+1 WHERE id=?", (body.attempt_id,))
    return {"hint": SKILLS[ITEM_MAP[row[0]]["skill"]]["rule"]}


class Answer(BaseModel):
    attempt_id: str = Field(max_length=100)
    answer: str = Field(max_length=2000)


@app.post("/api/answer")
def answer(body: Answer, authorization: str | None = Header(None)):
    token, _ = identity(authorization)
    with db() as conn:
        # One transaction prevents duplicate evidence from retries or concurrent submissions.
        conn.execute("BEGIN IMMEDIATE")
        raw = conn.execute(
            "SELECT state FROM learners WHERE token=?", (token,)
        ).fetchone()
        states = {k: State(**v) for k, v in json.loads(raw[0]).items()}
        row = conn.execute(
            "SELECT item,started,hints FROM issued WHERE id=? AND token=? AND used=0",
            (body.attempt_id, token),
        ).fetchone()
        if not row:
            raise HTTPException(409, "Exercise expired or already answered.")
        item = ITEM_MAP[row[0]]
        result = check(item, body.answer)
        now = time.time()
        elapsed = int(max(0, now - row[1]) * 1000)
        repeats = conn.execute(
            "SELECT COUNT(*) FROM issued WHERE token=? AND item=? AND used=1",
            (token, item["id"]),
        ).fetchone()[0]
        evidence_weight = 1 / (1 + repeats)
        if result["correct"] is not None:
            states[item["skill"]] = update(
                states.get(item["skill"], State()),
                result["correct"],
                now,
                result["error"],
                elapsed,
                row[2],
                evidence_weight=evidence_weight,
            )
        # No raw answer or free-writing text is persisted.
        event = {
            "item": item["id"],
            "prior_item_attempts": repeats,
            "evidence_weight": evidence_weight,
            "skill": item["skill"],
            "correct": result["correct"],
            "error": result["error"],
            "response_ms": elapsed,
            "hints": row[2],
            "at": now,
        }
        conn.execute(
            "UPDATE learners SET state=? WHERE token=?",
            (json.dumps({k: asdict(v) for k, v in states.items()}), token),
        )
        conn.execute("INSERT INTO events VALUES (?,?)", (token, json.dumps(event)))
        conn.execute("UPDATE issued SET used=1 WHERE id=?", (body.attempt_id,))
    return result


class Scenario(BaseModel):
    skill: str
    sessions: int = Field(default=3, ge=0, le=100)


@app.post("/api/simulate")
def simulate(body: Scenario, authorization: str | None = Header(None)):
    _, states = identity(authorization)
    if body.skill not in SKILLS:
        raise HTTPException(422, "Unknown skill")
    s = states.get(body.skill, State())
    now = time.time()
    return {
        "before": decayed(s, now),
        "after": project(s, body.sessions, now),
        "assumption": "One learning opportunity per session; fixed learn rate, no elapsed-time forgetting. Illustrative, not a causal promise.",
    }


@app.get("/api/export")
def export(authorization: str | None = Header(None)):
    result = state(authorization)
    token, _ = identity(authorization)
    with db() as conn:
        result["events"] = [
            json.loads(r[0])
            for r in conn.execute(
                "SELECT event FROM events WHERE token=? ORDER BY rowid", (token,)
            )
        ]
    return result


@app.delete("/api/session")
def delete(authorization: str | None = Header(None)):
    token, _ = identity(authorization)
    with db() as conn:
        for table in ("learners", "events", "issued"):
            conn.execute(f"DELETE FROM {table} WHERE token=?", (token,))
    return {"deleted": True}


DIST = Path(__file__).resolve().parents[1] / "frontend/dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(DIST / "index.html")
