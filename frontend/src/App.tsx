import React, { useEffect, useState } from "react";
import "./style.css";
import type { Skill, Snapshot, Task } from "./types";
import { ExerciseCard } from "./components/ExerciseCard";
import { TwinExplorer } from "./components/TwinExplorer";
import { DataControls } from "./components/DataControls";
import { SkillMap } from "./components/SkillMap";
export function App() {
  const [token, setToken] = useState(
    sessionStorage.getItem("twin-token") || "",
  );
  const [graph, setGraph] = useState<Skill[]>([]),
    [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [task, setTask] = useState<Task | null>(null);
  const [view, setView] = useState("learn"),
    [answer, setAnswer] = useState(""),
    [feedback, setFeedback] = useState(""),
    [done, setDone] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [hint, setHint] = useState("");

  async function api(
    path: string,
    method = "GET",
    body?: unknown,
    credential = token,
  ) {
    const r = await fetch("/api/" + path, {
      method,
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + credential,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!r.ok)
      throw new Error(
        (await r.json()).detail || "Could not connect. Please try again.",
      );
    return r.json();
  }
  async function safe(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function load(credential = token, writing = false) {
    setSnapshot(await api("state", "GET", undefined, credential));
    setTask(
      await api(
        writing ? "next?writing=true" : "next",
        "GET",
        undefined,
        credential,
      ),
    );
    setAnswer("");
    setFeedback("");
    setHint("");
    setDone(false);
  }
  useEffect(() => {
    fetch("/api/graph")
      .then((r) => r.json())
      .then((d) => setGraph(d.skills))
      .catch(() => setError("Start the API server to begin."));
    if (token) void safe(() => load());
  }, []);
  async function start() {
    const d = await api("session", "POST");
    sessionStorage.setItem("twin-token", d.token);
    setToken(d.token);
    await load(d.token);
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await safe(async () => {
      const r = await api("answer", "POST", {
        attempt_id: task!.attempt_id,
        answer,
      });
      setFeedback(r.feedback);
      setDone(true);
      setSnapshot(await api("state"));
    });
  }
  async function erase() {
    await api("session", "DELETE");
    sessionStorage.removeItem("twin-token");
    setToken("");
    setSnapshot(null);
    setTask(null);
  }

  return (
    <>
      <header>
        <a className="brand" href="/">
          ✳{" "}
          <span>
            grammar garden<small>Small steps. Growing skills.</small>
          </span>
        </a>
        <span className="tag">RESEARCH DEMO · ADULT SUPERVISION</span>
      </header>
      <main>
        <nav aria-label="Main view">
          <button
            className={view === "learn" ? "active" : ""}
            onClick={() => setView("learn")}
          >
            My learning
          </button>
          <button
            className={view === "twin" ? "active" : ""}
            onClick={() => setView("twin")}
          >
            Twin explorer
          </button>
          <button
            className={view === "data" ? "active" : ""}
            onClick={() => setView("data")}
          >
            My data
          </button>
        </nav>
        <div role="alert" className="error">
          {error}
        </div>
        {!token ? (
          <section className="welcome">
            <div className="eyebrow">A LITTLE PRACTICE, EVERY DAY</div>
            <h1>
              Let your grammar
              <br />
              grow.
            </h1>
            <p>
              Try a small word puzzle. Get a helpful tip.
              <br />
              Watch your learning garden grow with you.
            </p>
            <button
              disabled={busy}
              className="primary"
              onClick={() => safe(start)}
            >
              Start a demo garden ↗
            </button>
            <p className="muted">
              For adults exploring a learning prototype with children.
              <br />
              No names, email addresses, or personal stories needed.
            </p>
          </section>
        ) : (
          <>
            <div className="heading">
              <div>
                <div className="eyebrow">
                  {view === "twin"
                    ? "UNDERSTAND YOUR DIGITAL TWIN"
                    : "YOUR LEARNING GARDEN"}
                </div>
                <h1>
                  {view === "learn"
                    ? "One small step today."
                    : view === "twin"
                      ? "See how your twin thinks."
                      : "You control your data."}
                </h1>
              </div>
              <div className="stats">
                <span>☀ {snapshot?.streak || 0} in a row</span>
                <span>✿ {snapshot?.badges || 0} mastery badges</span>
              </div>
            </div>
            {view === "learn" && task && (
              <ExerciseCard
                graph={graph}
                task={task}
                answer={answer}
                setAnswer={setAnswer}
                done={done}
                busy={busy}
                submit={submit}
                safe={safe}
                api={api}
                load={load}
                token={token}
                hint={hint}
                setHint={setHint}
                feedback={feedback}
              />
            )}
            {view === "twin" && task && (
              <TwinExplorer
                graph={graph}
                task={task}
                busy={busy}
                safe={safe}
                api={api}
              />
            )}
            {view === "data" && (
              <DataControls busy={busy} safe={safe} api={api} erase={erase} />
            )}
            {view !== "data" && (
              <SkillMap graph={graph} snapshot={snapshot} view={view} />
            )}
          </>
        )}
        <footer>
          Grammar Garden · Explainable learning, one answer at a time.{" "}
          <span>Prototype — estimates are not diagnoses.</span>
        </footer>
      </main>
    </>
  );
}
