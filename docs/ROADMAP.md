# AIM development roadmap

**Status:** Phase 1 implemented; later phases proposed.

**Goal:** help clinicians interpret reported pharmacogenetic results, understand
applicable guidance, and investigate unresolved questions with traceable evidence.
Development currently uses fictional cases.

## Target workflow

Clinician question or patient description → reviewed patient facts → relevant
evidence and computed assessment → cited explanation and follow-up.

Python determines which structured recommendations apply. The model interprets
language, asks useful questions, retrieves explanatory evidence, and selects
investigation steps. Patient facts and prescribing conditions remain explicit.

## Phases

### 1. Structured assessment — implemented

- Accept a patient JSON and retrieve live CPIC evidence or an explicit snapshot.
- Match reported HLA results and treatment conditions in Python.
- Report source guidance, missing facts, conditions, and provenance.
- Scope: fictional adults, first-time carbamazepine. Input is reported allele
  status; raw sequencing and allele calling are outside this phase.
- Maintain this model-free assessment as the baseline for later work.

### 2. Conversational intake

- Accept a question or patient description alongside the existing JSON input.
- Extract draft facts with supporting text; identify unknowns and contradictions.
- Let the user review and correct facts before patient-specific assessment.
- Ask focused questions when a missing fact changes the applicable guidance.
- Benchmark candidate models on extraction quality, memory, and latency on
  Windows and macOS before selecting a runtime.

**Acceptance:** handle paraphrases, negation, ambiguous allele names, missing tests,
and corrections without inventing facts. Reviewed inputs must reproduce baseline
findings. Compare effort and errors against manual JSON entry.

### 3. Evidence questions and explanations

- Retrieve approved guideline passages, tables, and footnotes alongside CPIC records.
- Answer general guideline questions and explain an existing patient finding.
- Link claims to source passages, dates, versions, and document locations.
- Keep computed recommendations visible alongside the explanation; disclose missing
  or conflicting evidence.
- Start with section/text search; evaluate retrieval before adding embeddings.

**Acceptance:** review retrieval coverage, citation support, preserved conditions,
and explanation clarity. A citation must support its associated claim.

### 4. Adaptive investigation

- Let a bounded coordinator choose among clarification, assessment, recommendation
  lookup, guideline search, and completion based on the current question and results.
- Validate tool names and arguments; keep accepted facts and evidence in application state.
- Require a completed assessment for patient-specific findings. General evidence
  questions can be answered without constructing a patient case.
- Set turn, retry, timeout, and latency limits. Return verified partial results when
  a limit or service failure prevents completion.
- Keep an action/source log and treat retrieved documents as evidence.

**Acceptance:** demonstrate distinct action sequences for complete cases, missing
context, and guideline questions. Test malformed calls, misleading source text,
service failures, and exhausted limits. Retain adaptive planning where it improves
results or reduces unnecessary questions and tool calls.

### 5. Clinician workspace

- Bring reviewed patient facts, conversation, assessment, and sources into one interface.
- Support corrections and follow-ups within the same case; invalidate affected findings.
- Show unresolved conditions, evidence dates, and source-linked exports.
- Begin with local fictional sessions; decide storage and data handling before
  introducing persistent or real patient records.

**Acceptance:** reviewers can complete tasks, inspect sources, and correct facts
without reading code. Obtain clinician feedback before expanding coverage.

### 6. Broader clinical coverage

- Add one reviewed medication/gene use case at a time, with defined populations,
  result formats, recommendation conditions, and exclusions.
- Introduce medication-specific adapters when a second use case requires them.
- Consider standardized lab-result or PharmCAT-report imports before raw sequencing.
- Add label or interaction sources for defined questions; distinguish supported
  assessments from evidence-only answers and unsupported requests.

**Acceptance:** source review, condition-specific tests, missing-data behavior,
regression checks, and reviewer approval for each added use case.

### 7. Optional new-evidence review

- Search bounded publication sources for a supported drug/gene question.
- Record search dates, inclusion choices, and access limitations.
- Extract study populations, genetic results, exposures, outcomes, and limitations
  into a source-linked evidence table.
- Distinguish supplemental studies from current guidelines; reviewed publications
  do not automatically change the assessment rules.

**Acceptance:** manually check extraction and conclusions, and confirm a recurring
clinician need. This phase is optional.

## Design sources

These systems inform individual features; they are not project dependencies.

| Source | Approach informing AIM |
| --- | --- |
| [PharmCAT](https://pharmcat.clinpgx.org/) | Computable guideline interpretation and transparent reports (Phases 1, 6) |
| [CoVaPh](https://aclanthology.org/2026.iwsds-1.42.pdf) | Query normalization, fact extraction, structured and narrative evidence (2, 3) |
| [OpenEvidence](https://www.openevidence.foundation/announcements/introducing-the-openevidence-model-family) | Clinical questions, clarification, deeper evidence investigation (2–4) |
| [ClinicalKey AI](https://www.elsevier.com/products/clinicalkey/clinicalkey-ai) | Conversational explanations and inspectable sources (3, 5) |
| [TxAgent](https://arxiv.org/html/2503.10970v1) | Iterative tool selection adapted to a bounded clinical task (4) |
| [PGxAI-Recommender](https://www.nature.com/articles/s41746-026-02590-w) | Publication retrieval and structured study extraction (7) |

## Evaluation and next decisions

Use fixed fictional cases and a held-out set to compare the structured baseline,
direct model answers, and the grounded assistant. Measure fact errors, matching
accuracy, citation support, task completion, latency, and user effort. Record model
and evidence versions. Software evaluation is separate from clinical validation.

Before each phase, specify its inputs, outputs, failure behavior, and acceptance
checks; implement and review it in small blocks.

**Next:** agree representative clinician questions and the fact-review experience
for Phase 2, then benchmark models. Decide interface, source licensing, storage,
and additional medication coverage when their phases begin.
