import React from "react";
import type { Skill, Snapshot } from "../types";
import { pct } from "../format";

type Props = { graph: Skill[]; snapshot: Snapshot | null; view: string };
export function SkillMap({ graph, snapshot, view }: Props) {
  return (
    <section className="map">
      <div className="row">
        <h2>
          {view === "twin"
            ? "Mastery estimates & learning paths"
            : "Your growing skills"}
        </h2>
        <span className="muted">✿ badge at 85% estimated mastery</span>
      </div>
      <div className="skills">
        {graph.map((s) => {
          const state = snapshot?.skills[s.id];
          return (
            <article key={s.id}>
              <div className="row">
                <strong>{s.label}</strong>
                <span>{pct(state?.mastery ?? 0.35)}</span>
              </div>
              <progress max="1" value={state?.mastery ?? 0.35} />
              <small>
                {state?.attempts
                  ? `${state.attempts} tries`
                  : "Not yet practiced · prior estimate"}
              </small>
              {view === "twin" && (
                <>
                  <p className="muted">
                    Suggested foundations:{" "}
                    {s.prerequisites.length
                      ? s.prerequisites
                          .map((p) => graph.find((g) => g.id === p)?.label)
                          .join(", ")
                      : "Start here"}
                  </p>
                  <small>
                    Recent errors:{" "}
                    {state?.errors.map((e) => e.type).join(", ") ||
                      "none observed"}
                  </small>
                  <p className="muted">
                    Last response: {state?.response_ms || 0} ms · hints:{" "}
                    {state?.hints || 0}
                  </p>
                </>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
