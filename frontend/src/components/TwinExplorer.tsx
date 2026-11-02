import React, { useState } from "react";
import type { Skill, Task, Api, RunAction } from "../types";
import { pct } from "../format";

type Props = {
  graph: Skill[];
  task: Task;
  busy: boolean;
  safe: RunAction;
  api: Api;
};
export function TwinExplorer({ graph, task, busy, safe, api }: Props) {
  const [scenario, setScenario] = useState("articles");
  const [sessions, setSessions] = useState(3);
  const [projection, setProjection] = useState("");
  return (
    <div className="layout">
      <section className="card">
        <div className="eyebrow">NEXT RECOMMENDATION</div>
        <h2>{graph.find((s) => s.id === task.exercise.skill)?.label}</h2>
        {task.exercise.type !== "writing" && task.predicted_success !== null ? (
          <>
            <div className="big">{pct(task.predicted_success)}</div>
            <p>estimated chance of a correct answer</p>
          </>
        ) : (
          <p className="muted">
            Unscored writing — no success prediction or mastery update.
          </p>
        )}
        <p>{task.reason}</p>
        <p className="muted">
          Prior 35% · learn 12% · slip 10% · guess 20%
          <br />
          Forgetting half-life: 30 days. Provisional, uncalibrated parameters.
        </p>
      </section>
      <section className="card">
        <h2>What if we practice?</h2>
        <label>
          Grammar skill
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
          >
            {graph.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Learning opportunities
          <input
            type="number"
            min="0"
            max="100"
            value={sessions}
            onChange={(e) => setSessions(+e.target.value)}
          />
        </label>
        <button
          disabled={busy}
          onClick={() =>
            safe(async () => {
              const r = await api("simulate", "POST", {
                skill: scenario,
                sessions,
              });
              setProjection(
                `${pct(r.before)} → ${pct(r.after)}. ${r.assumption}`,
              );
            })
          }
        >
          Explore scenario ↗
        </button>
        <p aria-live="polite">{projection}</p>
      </section>
    </div>
  );
}
