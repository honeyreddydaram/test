import React from "react";
import type { Api, RunAction } from "../types";
import { pct } from "../format";

type Props = {
  busy: boolean;
  safe: RunAction;
  api: Api;
  erase: () => Promise<void>;
};
export function DataControls({ busy, safe, api, erase }: Props) {
  return (
    <section className="card">
      <h2>Your garden, your choice.</h2>
      <p>
        This local demo stores estimated skills and interaction metadata. It
        does not store your typed answers. Your session key stays in this
        browser tab.
      </p>
      <button
        disabled={busy}
        onClick={() =>
          safe(async () => {
            const data = await api("export");
            const url = URL.createObjectURL(
              new Blob([JSON.stringify(data, null, 2)], {
                type: "application/json",
              }),
            );
            const a = document.createElement("a");
            a.href = url;
            a.download = "my-twin.json";
            a.click();
            URL.revokeObjectURL(url);
          })
        }
      >
        Download my data
      </button>{" "}
      <button disabled={busy} className="danger" onClick={() => safe(erase)}>
        Delete my demo data
      </button>
      <p className="muted">
        Closing the tab loses the session key. Delete your demo data before
        leaving. A real child pilot needs consent, school approval, and ethical
        review.
      </p>
    </section>
  );
}
