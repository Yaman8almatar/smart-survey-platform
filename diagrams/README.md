# Diagrams

Iteration 0 outputs (Agile Modeling: initial requirements and architecture envisioning), 2026-10-30, are PNG exports.
Increment 1 diagrams (2026-11-13, TASK-25) are Mermaid sources in Markdown files, which GitHub renders (D-141).
Each source file starts with a Basis block and ends with a legend table.

| Diagram | Source | Exports | Tool |
|---|---|---|---|
| Class diagram: 11 domain classes and their enumerations (Increment 2) | `class-diagram.md` | `exports/class-diagram.png` | Mermaid `classDiagram` |
| ER diagram: 11 tables, columns, keys and constraints table (Increment 2) | `erd.md` | `exports/erd.png` | Mermaid `erDiagram` |
| State machine diagram: survey lifecycle (FR-11, FR-12) (Increment 2) | `state-survey-lifecycle.md` | `exports/state-survey-lifecycle.png` | Mermaid `stateDiagram-v2` |
| State machine diagram: sentiment analysis result (T-9, FR-05) (Increment 2) | `state-sentiment-result.md` | `exports/state-sentiment-result.png` | Mermaid `stateDiagram-v2` |
| Component diagram: tiers, layers, the analysis worker and the sentiment gateway (Increment 2) | `component-diagram.md` | `exports/component-diagram.png` | Mermaid `flowchart` |
| Data-flow diagram: sentiment analysis pipeline (FR-05, D-055) (Increment 2) | `dfd-sentiment.md` | `exports/dfd-sentiment.png` | Mermaid `flowchart` |
| Sequence diagram UC-02 Manage demographic profile (FR-02) | `sequence-uc02-profile.md` | `exports/sequence-uc02-profile.png` | Mermaid `sequenceDiagram` |
| Sequence diagram UC-04 Answer a survey, draft and resume, quality evidence (FR-06, FR-04) (Increment 2) | `sequence-uc04-answer.md` | `exports/sequence-uc04-answer.png` | Mermaid `sequenceDiagram` |
| Activity diagram: FR-04 quality rules, version 1 (Increment 2) | `activity-fr04-quality-rules.md` | `exports/activity-fr04-quality-rules.png` | Mermaid `flowchart` |
| Sequence diagram UC-06 View answered surveys (FR-01) | `sequence-uc06-answered.md` | `exports/sequence-uc06-answered.png` | Mermaid `sequenceDiagram` |
| Initial class diagram: 9 domain classes (Iteration 0, 2026-10-30; kept as a record, superseded by `class-diagram.md`) | - | `class-diagram.png` | Mermaid |
| Use case diagrams: Respondent, Provider, Admin | - | `use-case-respondent.png`, `use-case-provider.png`, `use-case-admin.png` | UML 2.5 notation (preliminary) |

PNG exports for the report and the deck are in `exports/`, rendered with mermaid-cli 12.2.0 (scale 2, white
background, `useMaxWidth` false; the class diagram with `--size 3700`): the UC-02 and UC-06 sequence diagrams from the
sources at develop 337648a, the UC-04 sequence and FR-04 activity diagrams from the sources at develop 9fd4097
(D-205), and the class, ER, two state machine, component and data-flow diagrams from the sources at develop 59f1957
(D-248). Export again when a source changes.

The architecture diagram is on slide 9 of the Seminar 1 deck in documentation/graduation-1/ (Iteration 0: it shows
Django 4.2 and the sentiment model as an external API; `component-diagram.md` is the current architecture).

## Rules
- Architecture: tiers Client / Application / Data; layers Presentation / Business / Data Source
  (Fowler, Patterns of Enterprise Application Architecture, Ch. 1). The Data Source layer holds the repositories
  and the sentiment gateway with its two adapters: the local model (default) and the Hugging Face router. Service Layer, Repository, Active Record and Gateway are
  patterns, not layers.
- Use cases are drawn at user-goal level: no "Log in" use case and no include or extend relations
  (Larman, Applying UML and Patterns, 2nd ed., Ch. 6).
- Requirement IDs are those of the Product Backlog: FR-01..FR-20 for Graduation 1.
- Diagrams are drawn from the code on develop: every class, column and message exists at the commit named in the
  Basis block.

## Done in Increment 1
- ERD with relational schema and constraints: `erd.md`, Mermaid `erDiagram` (D-141).
- Sequence diagrams for UC-02, UC-04 and UC-06.

## Done in Increment 2
Drawn from develop f3c96d4 (2026-11-20, TASK-46), after FR-03, T-9, FR-05 and FR-04:
- `class-diagram.md`: redrawn, 11 classes with `ResponseQuality`.
- `erd.md`: redrawn, 11 tables with `response_quality`.
- `sequence-uc04-answer.md`: redrawn with the start mark, the timings, the install ID, the evidence capture and the
  analysis worker.
- `activity-fr04-quality-rules.md`: new, the FR-04 quality rules, version 1.

Drawn from develop 59f1957 (2026-11-27, D-248), after FR-07, FR-09, FR-14, FR-16, FR-08, FR-12, FR-11, FR-13 and FR-15:
- `class-diagram.md` and `erd.md`: the shuffle switches (migration 0014), the review fields and PENDING_REVIEW (0015),
  the schedule, the response limit and PAUSED (0016), and `email_verified` (0017).
- `state-survey-lifecycle.md`: new, the five survey states and every transition with its trigger and guard.
- `state-sentiment-result.md`: new, the worker's states of a sentiment result with the retry rules.
- `component-diagram.md`: new, the two processes (web and analysis worker), the layers and the sentiment gateway.
- `dfd-sentiment.md`: new, the sentiment pipeline from the submit to the provider's summary (D-055).

## Planned in later increments
Drawn when the backlog item that needs them is pulled (Agile Modeling, model storming): one sequence diagram per
main use case built in Increment 2 (UC-10 targeting and reach, UC-14 review survey, UC-12 view analytics), and the
diagrams of FR-10 when it is built. The class and sequence diagrams do not show the service methods added from
TASK-48 on; the class diagram shows domain classes only.
