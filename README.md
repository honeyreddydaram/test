# Grammar Garden: an explainable learner digital twin

A local React/TypeScript + FastAPI + SQLite research prototype for children under 12, with adult supervision. No real children participated. The seed bank is a small demonstration, not a validated curriculum or child-ready product.

## Run

Python 3.12 and Node 22+ are recommended. From this directory:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
cd frontend
npm ci --cache /tmp/twin-npm-cache
npm run build
cd ..
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Build before starting the API, because the static mount is registered on import. For development run the API and `cd frontend && npm run dev` in separate terminals; Vite proxies `/api` to port 8000. Use the learner and twin tabs to answer, inspect estimates, and explore scenarios. Optional writing is deliberately unscored.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m backend.simulation
```

The simulator overwrites `reports/simulation.json` using seed 20261102. It uses only the standard library. Python dependencies are fully pinned in `requirements.lock.txt`, direct dependencies in `requirements.txt`; npm dependencies are pinned by `frontend/package-lock.json`. Parameters live in `config.json`. The reference frontend assumes default parameter labels; update those labels if changing the configuration.

## Read the design

- `data/skills.json`: 18 concepts, scaffold links, morphology and local error feedback.
- `data/error_taxonomy.json`: flat error catalog, with an explicit unclassified category.
- `data/exercises.json`: 19 curated demo items across all five exercise formats.
- `backend/model.py`: pure BKT, forgetting, prediction and illustrative projection.
- `backend/engine.py`: exact-key checking, conservative error diagnosis, policy and generation gate.
- `backend/generation.py`: optional OpenAI-compatible LLM integration; disabled without credentials.
- `backend/app.py`: local session isolation, SQLite, evidence API and static frontend.
- `backend/simulation.py`: known latent learner benchmark and prediction metrics.
- `reports/design.md`: design reasoning for all seven phases, equations, results and limits.

`GET /docs` exposes the API schema. API assessment never sends answer keys to the browser. Unknown wrong answers get `unclassified`, rather than a fabricated misconception. Wrong answers are not stored as raw text. A hint is recorded server-side and weakens evidence. Duplicate submission of the same exercise is rejected to avoid counting retries as independent observations. The pure model additionally accepts a retry count for future multistep tasks.

## Optional LLM generation

Set `LLM_API_KEY`, optionally `LLM_URL` and `LLM_MODEL`, in your environment, never in source control. Invoke `backend.generation.generate()` from Python. Only public seed templates are sent, never learner records. The adapter asks for an exercise and short explanation, but the accepted exercise must exactly match a deterministic curated template and the explanation must match its approved rule. The server supplies its own key. Novel content is rejected for independent review. This intentionally restrictive baseline demonstrates generation with verification; it is not an open-ended grammar verifier. Remote generation was not tested without credentials; the gate is tested locally. The default UI uses the seed bank offline.

## Privacy and research boundaries

This is a **local, single-browser research demo**, not a service for unsupervised child accounts. A random bearer token separates sessions; it is pseudonymous, not guaranteed anonymous. Keep the token private. No names, emails, birthdays, IP logs or raw answers are stored by the application. Disable HTTP access logs if operating with real users. Metadata includes item skill, error category, timing, hint count and timestamp. SQLite is unencrypted. Delete removes application rows, not a forensic erasure of database pages/backups. No analytics or student-facing remote LLM is enabled. Fonts use system fallbacks and no external font requests.

The My data view exports all interaction events and current state, or deletes all rows for the session. Session keys are tab-scoped: delete before closing the tab, since there is no identity-based recovery. There is no retention scheduler yet. Before a child pilot: parental consent, school approval and ethics review, age-appropriate accessibility/usability review, deployment security, retention and backup-erasure policies, validated exercises and review of applicable local law. This repo does not collect consent or claim those reviews have happened.

## Verification limits

Backend unit/integration tests and a production TypeScript/Vite build are automated. The UI has not had a browser or child usability audit. Simulation outcomes cannot establish an educational benefit. In the checked seed, the adaptive policy performs worse than fixed sequencing; see the report rather than assuming adaptivity is better.
