# Design and evaluation report

## Scope and audience

The user clarified that learners are mostly children under 12. We completed all phases without approval pauses as requested. Time budget was unspecified; the implementation prioritizes a small explainable research prototype. The UI uses short prompts, one exercise at a time, gentle error feedback, progress bars, correct-answer streaks and mastery badges. There are no timers, public leaderboards or personal-information prompts. The broad graph includes later material such as conditionals; suitability must be selected by an educator for the particular child, language background and reading level. Under 12 is not a single proficiency level.

## Phase 1: skill and error map

The JSON graph has 18 nodes, including bases, prefixes, suffixes, silent-e deletion, consonant+y changes and consonant doubling. Prerequisite edges form a DAG. They describe useful teaching scaffolds, not validated cognitive requirements. For example, plurals support agreement and determiner choices; present forms support past and future forms. Past spelling depends on three morphology rules. This is deliberately modest coverage: it omits many tense contrasts, pronouns, relative clauses, modals and passive voice.

Error IDs belong to concepts. Exact seed distractors diagnose errors such as `overgeneralized_ed` for *goed*, `retained_final_e` for *makeing*, and `wrong_article` for *a apple*. An unmatched answer gets `unclassified`: an exact-key mismatch alone cannot establish a learner's misconception. Generic concept errors are a starting taxonomy, not an exhaustive linguistic annotation scheme. The spelling rules have exceptions; they are examples rather than universal rules. Regional spelling conventions need explicit handling before expansion.

## Phase 2: state and BKT

Each skill has a mastery probability, attempts, ten recent error events, last response time, hint count and last-practiced timestamp. The complete interaction history is stored separately without raw text. Unpracticed skills have a 0.35 prior; this is an assumed prior, not a diagnosis.

BKT assumes a hidden known/unknown state. Prior P(L)=.35, learning P(T)=.12, slip P(S)=.10, guess P(G)=.20 are illustrative defaults. With current decayed mastery m:

- Predicted correctness: q = m(1-S) + (1-m)G.
- Correct evidence: posterior = m(1-S) / [m(1-S)+(1-m)G].
- Incorrect evidence: posterior = m S / [m S+(1-m)(1-G)].
- Learning transition: m_next = posterior + (1-posterior)T.

Before an observation or prediction: m_decay = m × 2^(-elapsed_days/30). The model decays toward zero and assumes no spontaneous learning between observations. This is a simple baseline, not a fitted forgetting law; a floor or skill-specific half-lives may fit better. The interface applies decay when displaying state, without repeatedly storing decayed values. UTC timestamps and clamping negative intervals avoid backward-clock inflation.

Item difficulty can shift log-odds of predicted correctness. All current items have difficulty zero; the BKT update uses unshifted observation likelihoods. Do not enable nonzero difficulties without adding consistent item-conditioned slip/guess likelihoods in the update and fitting them. Compare alternatives such as PFA/logistic knowledge tracing only after establishing a held-out BKT baseline.

## Phase 3: evidence

Correctness and hints influence posterior mastery. To avoid treating assisted responses like independent unassisted evidence, raise observation likelihoods to power 1/(1+hints+retries) before applying Bayes. This is an explicit heuristic, not standard fitted BKT. The learning transition still applies after incorrect answers: practice can teach. Server-side hint counts and issue timestamps avoid trusting client-reported evidence. One issued attempt may update state once; concurrency is guarded by a SQLite transaction.

Response time is measured from issue to submission; it includes idle time. It is descriptive metadata only. Slow reading, disability, distractions and device differences make a time penalty unjustified without research. Error types populate concept-specific history, supporting explanations and future interventions; this prototype does not estimate separate misconception mastery. Retry weighting exists in the pure model; the UI uses fresh attempts instead of same-item retries.

## Phase 4: exercises and feedback

The bank supports fill-in, choose form, error correction, reordering and short writing. Exact deterministic keys control scoring; normalization ignores casing, repeated spaces and terminal punctuation because these items target forms rather than punctuation. Correction tasks explicitly ask for the corrected word; reordering asks for the whole sentence. Multiple valid keys must be enumerated before release. Curated content and distractors still need independent educator review.

The LLM adapter is an optional proposal source. Its exercise must match a curated template and its explanation must match the corresponding rule before acceptance; generated keys are discarded. This conservative gate cannot verify arbitrary novel grammar exercises. No LLM-only correctness judgments are accepted. Default feedback comes from the rule associated with a diagnosed error. LanguageTool is not installed: it can flag some issues but cannot prove a sentence is correct. Unrestricted free writing is explicitly unscored and causes no mastery update. The local app transmits it for ephemeral processing but does not persist it.

## Phase 5: policy and simulation

Eligibility requires prerequisite estimates of at least .60. Prefer predicted success in [.70,.85], ranked by distance to .775, with a repeated-item penalty. When no candidate meets the zone, explore a least-practiced eligible skill. Every choice returns a human-readable reason. The fallback is essential: a pure nearest-probability rule initially got stuck on mastered roots. This failure was found by simulation and corrected, and has a regression test.

The what-if view computes 1-(1-m)(1-T)^n for n learning opportunities, assuming no elapsed time and a fixed learning rate. It is an expected learning-transition illustration, not a personalized causal prediction. Calling these opportunities sessions is only defensible when a session contains exactly one target opportunity. The UI therefore says learning opportunities.

The simulator uses 100 synthetic learners, 200 interactions each, fixed seed 20261102, binary latent mastery, heterogeneous learn (.06–.18), slip (.05–.15) and guess (.10–.30), and paired random draws indexed by learner/skill/exposure. The model's defaults are intentionally imperfect. Synthetic latent learning has no prerequisite dependencies, so gating can withhold practice unnecessarily. It has no elapsed-time forgetting during the short run. This limits transfer to real learning and favors a coverage-oriented fixed policy.

## Phase 6: architecture

React/TypeScript → FastAPI assessment API → pure model/engine → SQLite state and event tables. The frontend never receives grading keys. The model has no HTTP/database dependencies and can be tested alone. The API identifies learners only through random tab-scoped bearer tokens; queries are parameterized. A local served build uses one origin and no cross-origin access. Authentication for actual accounts, rate limits, managed secrets, transport security, encryption, retention, backup erasure, observability and a consent mechanism remain deployment work. There is deliberately no public deployment of this child-oriented research demo.

## Phase 7: evaluation and interpretation

`simulation.json` records AUC (tie-aware ranking), threshold accuracy, Brier score, 10-bin expected calibration error and per-bin predicted/observed frequencies. These are next-answer, pre-update predictions. Accuracy alone can look good when many items are easy; calibration and Brier are needed. For real data, split by learner and hold out future interactions, fit parameters only on training data, and audit by relevant accessibility and language-background groups under approved data governance.

Learning quality uses known latent knowledge, not the twin's own estimate. Report the fraction reaching 85% of latent skills and a restricted mean time to that threshold, censoring failures at 200 attempts. This avoids falsely reporting only successful learners. Point estimates are descriptive; no confidence intervals or significance claims are supplied. The fixed policy cycles all 18 scored items. The adaptive policy has a small item bank and prerequisite restrictions, so superiority is not expected by construction.

Explainability is available through selection reasons, prerequisite links, observed errors and visible BKT parameters. Each recommendation's immediate state is visible; a production research audit should additionally persist the exact pre-decision snapshot and parameter version.

## Limitations and next steps

Fit and validate priors and observation models; introduce diverse validated items and format-specific guessing; review the graph with teachers; compare gating versus soft prerequisites; use stronger counterfactual learner models and multiple seeds with uncertainty intervals; add accessible child usability testing before any approved pilot. Do not tune to this single simulator and present the resulting gain as real-world learning evidence. No remote LLM credentials, actual learner study or browser usability audit were available here.

## Recorded benchmark results

Seed 20261102, 100 learners per policy, 200 attempts each. These are descriptive synthetic results.

| Metric | Adaptive | Fixed |
|---|---:|---:|
| Next-answer AUC | 0.8088 | 0.8053 |
| Accuracy | 0.7754 | 0.7591 |
| Brier score (lower better) | 0.1584 | 0.1672 |
| Calibration error (lower better) | 0.0102 | 0.0092 |
| Reached 85% latent skills | 33% | 46% |
| Restricted mean attempts to threshold | 183.13 | 169.22 |
| Mean final latent mastery | 78.17% | 83.89% |

Adaptive practice predicts answers somewhat better here but teaches less broadly within the budget. Better prediction is not evidence of better teaching. Fixed practice covers advanced skills immediately; the simulator has no prerequisite-dependent learning, while the adaptive policy gates those skills. Test soft prerequisites and more varied item banks in a prespecified follow-up.

Validation: all 19 tests passed, including writing, static serving and full-history export. Production TypeScript/Vite build passed and the built HTML returned HTTP 200 through FastAPI TestClient. Browser interaction and remote LLM calls were not exercised.
