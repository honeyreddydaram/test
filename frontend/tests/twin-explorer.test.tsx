import React from "react";
import assert from "node:assert/strict";
import { test } from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { TwinExplorer } from "../src/components/TwinExplorer";
import type { Task } from "../src/types";

const task: Task = {
  attempt_id: "demo",
  exercise: {
    id: "writing-1",
    skill: "past",
    type: "writing",
    prompt: "Write a made-up story.",
    options: [],
  },
  predicted_success: null,
  reason: "Unscored writing.",
};
function render(value: Task) {
  return renderToStaticMarkup(
    <TwinExplorer
      graph={[]}
      task={value}
      busy={false}
      api={async () => ({})}
      safe={async (action) => {
        await action();
      }}
    />,
  );
}
test("writing displays no numeric prediction, even if given a number", () => {
  for (const predicted_success of [null, 0.75]) {
    const html = render({ ...task, predicted_success });
    assert.match(html, /Unscored writing/);
    assert.doesNotMatch(html, /estimated chance of a correct answer/);
    assert.doesNotMatch(html, /class="big"/);
  }
});
test("scored tasks retain numeric predictions, including a legitimate zero", () => {
  for (const predicted_success of [0, 0.75]) {
    const html = render({
      ...task,
      predicted_success,
      exercise: { ...task.exercise, type: "fill" },
    });
    assert.match(html, new RegExp(`${predicted_success * 100}%`));
    assert.match(html, /estimated chance of a correct answer/);
  }
});
