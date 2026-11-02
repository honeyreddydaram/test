# Design and evaluation report

## Scope and audience

A local, adult-supervised research prototype for children under 12. No children participated. Under 12 is not one reading or proficiency level: educator review and a consented usability study remain necessary. The UI presents one puzzle, short feedback, progress estimates and light gamification. It never requests identities or personal stories. All seven phases are implemented as an explainable baseline with the limits below.

## Phase 1: grammar and error map

The DAG contains 18 concepts, including word bases, prefixes, suffixes, silent-e deletion, consonant+y changes and consonant doubling. Prerequisites describe useful teaching scaffolds, not validated cognitive requirements. Examples and feedback are in `data/skills.json`; `data/error_taxonomy.json` provides a flat catalog. Coverage is intentionally incomplete: pronouns, modals, passive voice and relative clauses are future work.

The bank now contains 90 scored items, five distinct prompts per concept, plus one unscored writing activity. Existing item IDs are preserved so stored histories remain usable. Distractors diagnose specific errors such as `overgeneralized_ed` for *goed*. Unknown wrong answers get `unclassified`: a key mismatch alone does not prove a misconception. Some taxonomy categories are broad concept-level errors. Rules have exceptions and regional variation; independent educator review remains necessary.

## Phase 2: learner state and BKT

Each concept stores mastery, attempts, ten recent error events, last response time, hint usage and last-practiced time. The full event history is separate. BKT assumes a hidden known/unknown state, with provisional prior .35, learning .12, slip .10 and guess .20. These are assumptions, not validated child-specific estimates.

For decayed mastery m, success probability is m(1-slip)+(1-m)guess. Correct-answer likelihoods are (1-slip, guess); incorrect-answer likelihoods are (slip, 1-guess). Bayes combines these with m to produce a posterior, then the learning transition adds (1-posterior)learn. Before an observation/prediction, mastery decays as m × 2^(-elapsed_days/30). This assumes a zero asymptote and no spontaneous learning; both require later validation.

Hints and retries weaken likelihood evidence by exponent 1/(1+hints+retries). Repeated completed items additionally use weight w=1/(1+prior_item_attempts), multiplying that exponent and the learning transition. This is a conservative heuristic, not standard fitted BKT or a model that distinguishes memorization from knowledge. Repeated success can still eventually raise mastery; transfer should be checked with unseen assessment items. Slow responses are recorded, not penalized, because reading, disability, interruptions and device differences confound speed.

All current item difficulties are zero. Nonzero logit difficulty is supported for prediction but would require consistent item-conditioned observation likelihoods before use in assessment. Format-specific guessing and fitted forgetting curves are future work. PFA/logistic knowledge tracing can be compared after establishing a held-out BKT baseline.

## Phase 3: interaction evidence

Issue times and hint counts are measured server-side. An issued attempt may update state once, enforced transactionally. Events store item ID, skill, correctness, error type, elapsed time, hints, timestamp, repetition count and evidence weight; raw answers are never persisted. Earlier stored events lack item/repetition fields, but issued records still support item counts. Repeated exposure is known at item level, not inferred from text.

Selection uses all issued-item counts, including skipped items, to avoid refresh-driven repetition. Assessment weights use completed repetitions only, because skipping an item is not evidence of knowledge. Misconceptions populate error histories; separate misconception mastery is not estimated. Retry weighting exists in the pure model, while the UI creates new attempts.

## Phase 4: exercises, generation and grading

The bank supports fill-in, correction, reordering, choose-form and writing. Grading uses explicit accepted keys with case, whitespace and terminal-punctuation normalization. Full-word affix answers are accepted: both `ness` and `kindness` answer the kind___ item. Prefix completions similarly accept affix or full word. Common full corrected sentences are accepted alongside corrected words. Arbitrary answer-containing substrings remain incorrect. Multiple valid answers must be deliberately enumerated rather than trusted to an LLM.

The optional OpenAI-compatible adapter proposes only known templates and explanations matching curated rules. It supplies no grading authority: generated keys are discarded and novel exercises are rejected pending review or deterministic rule proof. The default UI remains offline and uses the bank. Live generation was not tested without credentials. LanguageTool is not installed; even a grammar checker cannot prove arbitrary writing correct. Free writing is explicitly unscored, has a null success prediction, and does not update mastery. The Twin explorer hides numeric predictions for writing, with regression coverage on actual rendered components.

## Phase 5: policy and simulation

No skill is locked by prerequisites. For a concept, average max(0, .60-prerequisite_mastery)/.60 over its prerequisites, then multiply by .15 to produce a soft ranking penalty. Root concepts have zero penalty. Prefer skills in the .70–.85 predicted-success zone by distance to .775 plus that penalty. If no skill is in-zone, rank by least practice first and then the score. This preserves exploration even when foundations are weak. Recommendations explain probability, strategy, prerequisite penalty and item exposure.

After selecting a skill, choose its least-exposed item, avoiding an immediate repeat in ties. This creates variation without giving a skill more ranking influence merely because it has more items. Repetition weights reduce overconfidence when the finite bank is reused. Five items per skill improve the prototype but do not demonstrate transfer or constitute a validated curriculum.

The what-if projection is 1-(1-m)(1-learn)^n for n fresh opportunities, no elapsed-time forgetting and fixed learn rate. It is illustrative, not a personalized causal promise. Repeated opportunities may have a smaller modeled gain than this projection.

The benchmark compares soft prerequisites (`adaptive`), a hard-gating comparison (`hard_prerequisites`), and fixed round-robin sequencing on the same expanded bank and repeat weighting. Fixed items interleave skills rather than presenting a block of five questions per concept. There are 100 synthetic learners per policy and 200 interactions, seed 20261102. Binary latent mastery uses heterogeneous learn .06–.18, slip .05–.15 and guess .10–.30. Counterfactual draws are paired by learner/skill/exposure. The latent simulator has neither item memorization, prerequisite-dependent learning nor elapsed-time forgetting during its short run. Thus memorization did **not** explain the original simulated adaptive deficit; it is a plausible real-user risk, not a mechanism in that simulator. Adding items alone cannot improve true learning in this synthetic model. The hard/soft comparison is limited to this model.

## Phase 6: architecture and readability

React/TypeScript → FastAPI → pure model/engine → SQLite. The entry point is now just a bootstrap; `App.tsx` owns session/navigation state. `ExerciseCard`, `TwinExplorer`, `SkillMap` and `DataControls` have explicit props, shared types and a small formatting helper. Backend and tests use expanded formatting; the BKT implementation names its likelihoods and posterior calculations. Model functions have no HTTP/database dependencies. Existing API shapes and SQLite tables remain compatible; new metadata is embedded in event JSON.

Random tab-scoped bearer tokens provide local session isolation. SQL is parameterized and keys never reach the browser. This is not a public child-account service: authentication, transport security, rate limits, retention, encryption, backup erasure and consent capture require deployment work. The My data view exports all events and current estimates or deletes session rows. Deletion is application-level, not forensic SQLite/backups erasure. Closing a tab loses its key; delete before closing. No remote fonts, analytics or default remote LLM requests are used.

## Phase 7: evaluation and results

Prediction quality uses pre-update next-answer AUC, threshold accuracy, Brier score, ten-bin calibration error and calibration bins. Learning quality uses known latent knowledge, not the twin's own estimate. Report attainment of 85% latent skills and restricted mean attempts to that threshold, censoring at 200; this avoids reporting only successful learners. Results below are descriptive point estimates without confidence intervals or significance claims. The original run is archived in `simulation-original.json`; `simulation.json` is the current three-policy run.

| Metric | Soft prerequisites | Hard prerequisites | Fixed |
|---|---:|---:|---:|
| Next-answer AUC | 0.8025 | 0.8057 | 0.8021 |
| Accuracy | 0.7565 | 0.7737 | 0.7546 |
| Brier score | 0.1682 | 0.1581 | 0.1691 |
| Calibration error | 0.0184 | 0.0288 | 0.0178 |
| Reached 85% latent skills | 43% | 29% | 46% |
| Restricted mean attempts | 173.48 | 187.38 | 169.22 |


Explainability includes visible BKT assumptions, prerequisite links, error history and per-selection reasons. A research deployment should additionally persist parameter versions and exact pre-decision snapshots. Real-data evaluation should split by learner, hold out future interactions, fit only on training data, and assess calibration under approved data governance.

## Limitations and next steps

Soft prerequisites improve synthetic attainment relative to hard gating but do not establish superiority over fixed practice. The simulator has no prerequisite learning effects and therefore does not measure possible benefits of foundation practice. Add such effects, item-specific memory and unseen transfer probes; run multiple seeds with uncertainty intervals; fit parameters; validate item ambiguity and developmental suitability; test format-specific guessing and less restrictive generation with independent checks. Do not tune to one simulator and claim real-world efficacy. Before any child pilot, obtain parental consent, school approval and ethical review, plus accessible usability testing and deployment privacy/security review.

Validation: 24 backend unit/integration tests, two rendered-component frontend regression tests, and a production TypeScript/Vite build. Browser interaction, live LLM calls and child usability were not tested.
