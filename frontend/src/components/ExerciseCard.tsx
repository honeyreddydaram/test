import React from "react";
import type { Skill, Task, Api, RunAction } from "../types";
import { pct } from "../format";

type Props = {
  graph: Skill[];
  task: Task;
  answer: string;
  setAnswer: (value: string) => void;
  done: boolean;
  busy: boolean;
  submit: (event: React.FormEvent) => Promise<void>;
  safe: RunAction;
  api: Api;
  load: (credential?: string, writing?: boolean) => Promise<void>;
  token: string;
  hint: string;
  setHint: (value: string) => void;
  feedback: string;
};
export function ExerciseCard({
  graph,
  task,
  answer,
  setAnswer,
  done,
  busy,
  submit,
  safe,
  api,
  load,
  token,
  hint,
  setHint,
  feedback,
}: Props) {
  return (
    <div className="layout">
      <section className="card exercise">
        <div className="row">
          <span className="pill">
            {graph.find((s) => s.id === task.exercise.skill)?.label}
          </span>
          <span className="muted">{task.exercise.type} puzzle</span>
        </div>
        <h2>{task.exercise.prompt}</h2>
        <p className="muted">
          {["correct", "reorder"].includes(task.exercise.type)
            ? task.exercise.type === "correct"
              ? "Type the corrected word or sentence."
              : "Type the whole sentence."
            : task.exercise.type === "writing"
              ? "Write about a made-up character. This activity is unscored."
              : "Type or choose the missing word."}
        </p>
        <form onSubmit={submit}>
          {task.exercise.options.length > 0 ? (
            <div className="choices">
              {task.exercise.options.map((o) => (
                <button
                  type="button"
                  disabled={done || busy}
                  className={answer === o ? "selected" : ""}
                  key={o}
                  onClick={() => setAnswer(o)}
                >
                  {o}
                </button>
              ))}
            </div>
          ) : (
            <input
              aria-label="Your answer"
              value={answer}
              disabled={done || busy}
              onChange={(e) => setAnswer(e.target.value)}
              autoComplete="off"
              placeholder="Your answer goes here…"
            />
          )}
          <div className="actions">
            {!done ? (
              <>
                <button className="primary" disabled={busy || !answer.trim()}>
                  Check my answer →
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    safe(async () =>
                      setHint(
                        (
                          await api("hint", "POST", {
                            attempt_id: task.attempt_id,
                          })
                        ).hint,
                      ),
                    )
                  }
                >
                  A little hint
                </button>
              </>
            ) : (
              <button
                type="button"
                className="primary"
                disabled={busy}
                onClick={() => safe(() => load())}
              >
                Next puzzle →
              </button>
            )}
          </div>
        </form>
        <button
          disabled={busy}
          onClick={() =>
            safe(() => load(token, task.exercise.type !== "writing"))
          }
        >
          {task.exercise.type === "writing"
            ? "Back to scored puzzles"
            : "Try unscored writing"}
        </button>
        <p className="hint" aria-live="polite">
          {hint}
        </p>
        <p className="feedback" aria-live="polite">
          {feedback}
        </p>
      </section>
      <aside className="card">
        <div className="plant">♧</div>
        <h2>Practice helps you grow.</h2>
        <p>
          It is okay to make mistakes. Each answer helps your twin choose what
          to practice.
        </p>
        <hr />
        <p className="muted">
          Your twin is an estimate. A score is not a label for you.
        </p>
      </aside>
    </div>
  );
}
