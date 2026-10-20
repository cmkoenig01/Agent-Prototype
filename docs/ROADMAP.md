# AIM: phased roadmap for a clinician-facing PGx assistant

**Status: discussion draft, 2026-10-20. Only Phase 1 is implemented.**

This document records the intended capabilities and their dependencies. It is not
an instruction to implement all phases at once. Before each phase, agree its small
implementation plan, build in reviewable blocks, evaluate it, and update this document.

## 1. Purpose and product boundary

Help a clinician work through a pharmacogenetics question: identify the relevant
reported patient facts, find applicable evidence, expose unresolved conditions,
and explain the evidence with traceable sources.

The application should support one connected workflow rather than six products or
six artificial operating modes. Depending on the question, the clinician may want
to review a patient, understand a guideline, investigate an uncertainty, or inspect
new evidence. The same patient context and evidence records should carry across
those activities.

The current application is much narrower than PharmCAT: it matches reported HLA
allele statuses to carbamazepine guidance. It does not call variants, interpret raw
sequencing, or implement PharmCAT's full genotype/phenotype pipeline.

The intended audience is clinicians. The current users and reviewers are student
researchers and the genetics PI, using fictional cases. Clinical deployment is a
separate validation and governance decision, not an outcome of completing this roadmap.

## 2. Inspiration: what to borrow and why

These are design inspirations, not integrations, dependencies, endorsements, or
claims that our system will reproduce another system's performance. Product pages
describe advertised capabilities; research papers describe experiments, not proof
of benefit in routine clinical practice.

| Inspiration | Documented approach | Element useful to AIM | What we are not proposing to copy |
| --- | --- | --- | --- |
| [PharmCAT](https://pharmcat.clinpgx.org/) | Genetic data or outside calls are interpreted into guideline-based reports. | A transparent, independently testable computation layer and source-backed output. | Rebuilding a sequencing/allele-calling pipeline. |
| [CoVaPh](https://aclanthology.org/2026.iwsds-1.42.pdf) | Normalizes clinical questions, extracts information, and combines guideline retrieval with CPIC API data before answer synthesis. | Natural-language intake and the combination of structured recommendations with explanatory guideline passages. | Its model ensemble, fine-tuning program, or population-frequency machinery by default. |
| [OpenEvidence](https://www.openevidence.foundation/announcements/introducing-the-openevidence-model-family) | Describes clinical question answering, deeper evidence investigation, and requests for further clinical context. | A question-driven clinician workflow and clarification when context matters. | Assuming its proprietary internal architecture or advertised performance is transferable. |
| [ClinicalKey AI](https://www.elsevier.com/products/clinicalkey/clinicalkey-ai) | Conversational clinical queries with evidence-linked answers and source traceability. | Readable explanations, follow-up questions, and direct inspection of supporting passages. | Access to its licensed corpus or broad clinical coverage. |
| [TxAgent](https://arxiv.org/html/2503.10970v1) | Iteratively selects biomedical tools, inspects their results, and adapts its investigation. | An agent that chooses useful next actions based on the question and accumulated evidence. | A large tool universe, training pipeline, or autonomous treatment selection. |
| [PGxAI-Recommender](https://www.nature.com/articles/s41746-026-02590-w) | Retrieves publications/regulatory information, extracts study evidence, and produces guideline-style drafts. | A later, optional evidence-update panel with structured study summaries. | Automatically writing or replacing prescribing guidelines. |

## 3. One workflow, with distinct responsibilities

**Clinician input:** a question, patient description, or existing structured case.

**Assistant:** understands the request, proposes patient facts, identifies what needs
clarification, searches approved evidence, and explains retrieved material. Once
adaptive investigation is introduced, it also selects the next useful action.

**Python assessment core:** validates the accepted patient facts, retrieves structured
CPIC records, and computes the applicable finding and missing conditions.

**Evidence layer:** preserves exact source text, identifiers, URLs, dates, versions,
document sections, and evidence type. Structured guidance and explanatory passages
are related evidence items, not interchangeable content.

**Clinician report:** shows patient facts and their origins, the computed finding,
unresolved information, a cited explanation, and the evidence used. The clinician
can inspect or correct the facts and ask a follow-up without restarting the case.

JSON remains useful internally and for tests; clinicians should not have to author
JSON to ask a question. General evidence questions must also work without inventing
a patient or demanding irrelevant patient fields.

## 4. Phases and completion gates

| Phase | Deliverable | Status / prerequisite |
| --- | --- | --- |
| 1 | Deterministic patient assessment and evidence report | Implemented and pushed |
| 2 | Conversational intake and reviewed patient facts | Next phase to specify and evaluate |
| 3 | Guideline questions and cited explanations | Builds on Phase 2 and an approved evidence collection |
| 4 | Adaptive, bounded investigation | Requires reliable tools and evaluation from Phases 2–3 |
| 5 | A clinician workspace for the connected workflow | Requires useful conversations, not just a working model endpoint |
| 6 | Reviewed expansion of medications and clinical context | Only after the narrow workflow is useful |
| 7 | Optional new-evidence review | Deferred; does not block the core clinician assistant |

### Phase 1 — the current product

**Clinician task:** assess explicit, fictional adult first-time carbamazepine cases.
**Inspiration:** the computable recommendation/reporting approach illustrated by PharmCAT.

- Inputs: the existing patient JSON schema and live CPIC evidence; saved evidence is explicit.
- Processing: validate scope, preserve both HLA results, match records and conditions in Python.
- Output: source recommendation, missing facts, conditions, strength, identifiers, and citations.
- Delivery: one `aim-pgx --case ...` command, uv setup on macOS/Windows, and [current architecture PNG](architecture.png).

**Checkpoint:** application commit `13dcb99`; uv-only onboarding correction `f2b41f2`
on `kush/aim-prototype`. The baseline has 74 passing offline tests plus separate
live retrieval checks. These are software checks, not clinical validation.

**Keep:** the assessment command and tests remain available independently of later
model features. The teammate-owned `agent.py` remains separate and unchanged.

### Phase 2 — useful language understanding and clarification

**Clinician task:** describe a patient or ask a question without filling a JSON file.
**Inspiration:** CoVaPh's query normalization/information extraction and the contextual
conversations described by OpenEvidence and ClinicalKey AI.

**Build in order:**

1. Define fictional narrative cases and expected extracted facts before selecting a model.
2. Add a small model adapter. Verify endpoint, installed model, version/digest, supported
   output format, memory, and latency on Windows and the teammate's macOS runtime.
3. Extract candidate facts into a draft case, retaining the input text that supports each
   fact. Distinguish explicit facts, unknowns, contradictions, and user corrections.
4. Show the interpreted facts for review before patient-specific matching. Preserve
   unavailable information as unknown; do not infer results from ancestry or drug history.
5. Use the core's missing-information result to support focused follow-up questions.
   Corrections update the reviewed facts and trigger reassessment, not a second unrelated case.

**Interface proposal:** retain the existing LLM-free `--case` input; add `--question`
for a terminal conversation and later `--note` for a plain-text patient description.
A question may accompany a structured case. Exact argument combinations and session
behavior will be agreed in the Phase 2 implementation plan; no `demo` mode returns.

**Model value:** interpreting varied language and maintaining a useful clarification
conversation. Merely asking it to execute a fixed lookup sequence is not sufficient.

**Completion gate:** test paraphrases, negation, unreported tests, ambiguous allele
names, contradictory notes, and corrections. The reviewed facts must reproduce the
existing deterministic findings. Compare extraction effort and errors with manual
JSON entry. Reject invented facts in the agreed acceptance set; report failures,
rather than treating a successful API call as success.

### Phase 3 — evidence questions and grounded explanations

**Clinician task:** ask what guidance means, why a condition matters, or what evidence
supports the finding, without manually reading every record and linked document.
**Inspiration:** CoVaPh's structured-plus-narrative evidence and ClinicalKey AI's
traceable answers; OpenEvidence's question-driven evidence synthesis.

- Add an approved collection of carbamazepine/HLA guideline sections, tables, footnotes,
  and explanatory passages. Start with simple section/text retrieval; add embeddings
  only if retrieval evaluation demonstrates a need.
- Link passage evidence to structured records. Each item carries source identity,
  location, retrieval/version information, and the source text used for the answer.
- Permit general guideline questions as well as explanations of an existing patient finding.
- Let the model write an explanation supported by retrieved passages. Display the
  computed recommendation separately, so explanatory prose cannot replace its conditions.
- If evidence is missing, conflicting, or insufficient, state the limitation and show
  what was found. Do not answer from model memory as if a source had been retrieved.

**Completion gate:** evaluate retrieval relevance and coverage, citation accuracy,
claim support, preserved qualifications, and understandable wording. Check source
IDs automatically and have a knowledgeable reviewer assess whether cited passages
actually support the claims; citation presence alone is not factual verification.

### Phase 4 — adaptive investigation, not a fixed tool script

**Clinician task:** work through a question whose next useful step depends on the
patient facts, prior answers, and retrieved evidence.
**Inspiration:** TxAgent's iterative tool selection, adapted to a narrow clinician task.

- Introduce one bounded coordinator over small, tested actions: inspect case state,
  request a clarification, run the assessment, retrieve a recommendation, search a
  guideline section, and finish with a supported or incomplete answer.
- The model selects actions according to the task. A patient assessment, a request
  for explanation, and a missing-information conversation should have different traces.
- Python owns the tool allowlist, argument validation, accepted patient state, evidence
  provenance, and completion checks. General questions do not require a patient assessment;
  patient-specific prescribing findings do require successful computation.
- Keep a concise action/evidence log, not hidden chain-of-thought. Set turn, tool-call,
  retry, timeout, and latency budgets in the phase specification. On exhaustion,
  return the verified partial state and the unresolved issue.
- Treat retrieved text as evidence, not instructions. Tool failure or irrelevant
  retrieval must lead to a justified next step or explicit limitation, not repeated calls.
- Use a small handwritten controller first. A larger agent framework needs a concrete
  benefit demonstrated against that implementation.

**Completion gate:** show distinct successful traces for assessing a complete case,
asking for unavailable context, and answering a guideline explanation. Test malformed
calls, misleading source text, unavailable services, and exhausted budgets. Compare
with the fixed Phases 2–3 workflow; retain adaptive planning only where it improves
task completion, evidence coverage, or unnecessary-question/tool-call counts.

### Phase 5 — clinician workspace and usable review

**Clinician task:** review the case and evidence together, edit facts, ask follow-ups,
and inspect why the current answer was produced.
**Inspiration:** the clinician-centered interaction and source inspection of the
commercial evidence assistants; we are not claiming their implementation or validation.

- Build one lightweight interface after the terminal workflow is useful. Present a
  reviewed patient-context area, conversation, assessment result, and inspectable sources.
- Expose connected activities: **review a patient**, **ask/explain guidance**, and
  **explore supporting evidence**. They share state rather than duplicating pipelines.
- Mark facts as reported, extracted-but-unreviewed, unknown, or corrected. Corrections
  invalidate dependent findings; old results must not appear current.
- Show source dates, evidence mode, unresolved conditions, and action history in the
  places where they help the clinician interpret the result. Permit a source-linked export.
- Keep fictional local sessions initially. Persistent storage or real patient material
  requires an explicit data-handling decision before being added.

**Completion gate:** researchers and the PI can complete the target tasks without
reading code, see which facts and sources support the result, and correct an error.
Seek clinician feedback on usefulness and effort before expanding scope.

### Phase 6 — controlled expansion of clinical coverage

**Clinician task:** apply the same workflow to additional reviewed PGx questions.
**Inspiration:** PharmCAT's broader guideline coverage and TxAgent's specialized tools.

- Add one PI-prioritized medication/gene use case at a time. Define supported patient
  populations, result representations, recommendation conditions, and exclusions first.
- Refactor the current carbamazepine-specific schema into reviewed medication adapters
  when a second use case justifies it. Do not make an unrestricted model decide new rules.
- Consider imports of standardized lab results or PharmCAT reports before attempting
  raw sequencing interpretation. Preserve source and reviewed meaning of imported results.
- Add drug-label or interaction sources only for explicit clinical questions and with
  their own validation. A PGx assessment must not silently become comprehensive prescribing advice.
- Keep a visible capability registry: supported, unsupported, or evidence-only. A model
  recognizing a medication name does not establish support for patient assessment.

**Completion gate:** each added use case has source review, condition-specific tests,
missing-data behavior, regression checks, and reviewer sign-off. Existing cases must
continue to work. Do not expand medication, population, and evidence-source scope at once.

### Phase 7 — optional clinician-oriented new-evidence review

**Clinician task:** investigate what published evidence may explain or update an
existing guideline position, rather than conduct open-ended drug discovery.
**Inspiration:** PGxAI-Recommender's document retrieval and structured study extraction.

- Add a clearly labeled evidence-review activity only if clinicians or the PI identify
  a recurring need that guideline questions cannot answer.
- Search bounded sources for a selected supported drug/gene question. Record the query,
  search date, inclusion choices, publication types, and access limitations.
- Extract study population, genotype/result, exposure, outcomes, and limitations into
  a source-linked evidence table, then summarize agreements and differences.
- Keep current guideline guidance and additional publications distinguishable. New
  papers must not automatically modify the deterministic recommendations.
- Do not claim a systematic review, complete literature coverage, or a newly validated
  prescribing recommendation. Unavailable full text remains an explicit limitation.

**Completion gate:** manual checks of study extraction and conclusions, assessment
of whether the panel answers a real clinician question, and explicit labeling of
guideline versus supplemental evidence. This phase may be deferred indefinitely.

## 5. Evaluation throughout development

Maintain three comparison levels: the current structured assessment, direct model
answers without tools (evaluation only), and the grounded assistant. Use fixed,
fictional cases with paraphrases, missing facts, condition changes, and adversarial
or unsupported requests. Keep a held-out set separate from examples used to tune prompts.

| Question | What to measure |
| --- | --- |
| Are the patient facts correct? | Extraction errors, unsupported additions, contradiction handling, and correction success |
| Does the guideline match remain correct? | Agreement with reviewed structured cases, including missing results and conditional branches |
| Is the explanation grounded? | Supporting passages, accurate citations, unsupported claims, and preserved limitations |
| Does adaptation help? | Task completion versus fixed workflow, needless calls/questions, time to useful answer |
| Is it useful to a clinician? | Task effort, ability to inspect/correct, understandable output, and clinician feedback |
| Does it fail predictably? | Explicit outcomes under network/model failure, malformed tools, stale state, and budget exhaustion |

Report software/model evaluation separately from clinical validation. Record the model,
runtime, prompts, evidence versions, and test conditions; changing a model or source
requires the relevant evaluations again. Windows and macOS need actual runtime checks;
an installation succeeding on one machine does not prove model behavior on another.

## 6. Defaults and decisions to resolve before implementation

**Keep fixed:** one Python package, uv-managed dependencies, the LLM-free case command,
CPIC as the initial evidence authority, fictional adults, carbamazepine, no ancestry
substitution, explicit missing information, and source-backed outputs.

**Phase 2 kickoff decisions:** choose representative clinician questions with the PI;
agree the review/clarification experience; benchmark a local model against those tasks;
select the runtime/model and acceptable latency based on results. A hosted model is
an alternative to discuss, not a prerequisite or a silently introduced service.

**Later decisions:** source licensing and update policy, interface choice, whether
sessions need persistence, the next medication, and whether new-evidence review is useful.
Resolve these at the relevant phase rather than implementing speculative infrastructure now.

No fine-tuning, multi-agent ensemble, vector database, EHR integration, autonomous
prescription changes, or large framework is a default requirement. Introduce one
only after a specific task and evaluation justify it.

## 7. Review and change process

1. Select the next phase and agree its clinician task and success criteria.
2. Write the small implementation specification in this document before editing code:
   inputs/outputs, module changes, failure behavior, tests, and runtime requirements.
3. Implement one functional block and explain what enters it, what leaves it, and why it helps.
4. Review the block and its evidence; record limitations and the decision to continue or revise.
5. Commit the phase independently, update status here and the current architecture,
   and keep working setup/run instructions accurate on macOS and Windows.

**Immediate next planning topic:** Phase 2's input interpretation and clarification
workflow, using a handful of PI-reviewed fictional questions. Do not restore a model
merely to repeat the current deterministic sequence.
