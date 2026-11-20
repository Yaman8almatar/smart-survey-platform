# Diagrams

Iteration 0 outputs (Agile Modeling: initial requirements and architecture envisioning), 2026-10-30, are PNG exports.
Increment 1 diagrams (2026-11-13, TASK-25) are Mermaid sources in Markdown files, which GitHub renders (D-141).
Each source file starts with a Basis block and ends with a legend table.

| Diagram | Source | Exports | Tool |
|---|---|---|---|
| Class diagram: 11 domain classes and their enumerations (Increment 2) | `class-diagram.md` | `exports/class-diagram.png` (Increment 1) | Mermaid `classDiagram` |
| ER diagram: 11 tables, columns, keys and constraints table (Increment 2) | `erd.md` | `exports/erd.png` (Increment 1) | Mermaid `erDiagram` |
| Sequence diagram UC-02 Manage demographic profile (FR-02) | `sequence-uc02-profile.md` | `exports/sequence-uc02-profile.png` | Mermaid `sequenceDiagram` |
| Sequence diagram UC-04 Answer a survey, draft and resume, quality evidence (FR-06, FR-04) (Increment 2) | `sequence-uc04-answer.md` | `exports/sequence-uc04-answer.png` (Increment 1) | Mermaid `sequenceDiagram` |
| Activity diagram: FR-04 quality rules, version 1 (Increment 2) | `activity-fr04-quality-rules.md` | not rendered yet | Mermaid `flowchart` |
| Sequence diagram UC-06 View answered surveys (FR-01) | `sequence-uc06-answered.md` | `exports/sequence-uc06-answered.png` | Mermaid `sequenceDiagram` |
| Initial class diagram: 9 domain classes (Iteration 0, 2026-10-30; kept as a record, superseded by `class-diagram.md`) | - | `class-diagram.png` | Mermaid |
| Use case diagrams: Respondent, Provider, Admin | - | `use-case-respondent.png`, `use-case-provider.png`, `use-case-admin.png` | UML 2.5 notation (preliminary) |

PNG exports of the Increment 1 diagrams for the report and the deck are in `exports/`, rendered from the sources at
develop 337648a with mermaid-cli 12.2.0 (scale 2, white background). Export again when a source changes.
The class, ER and UC-04 sequence exports in `exports/` are still the Increment 1 renders: they do not show the
Increment 2 sources until the advisor renders the new ones; the activity diagram has no export yet.

The architecture diagram is on slide 9 of the Seminar 1 deck in documentation/graduation-1/.

## Rules
- Architecture: tiers Client / Application / Data; layers Presentation / Business / Data Source
  (Fowler, Patterns of Enterprise Application Architecture, Ch. 1). The Data Source layer holds the repositories
  and the gateway to the external sentiment service. Service Layer, Repository, Active Record and Gateway are
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

## Planned in later increments
Drawn when the backlog item that needs them is pulled (Agile Modeling, model storming): the component diagram
(moved to Increment 2 with the analysis worker, DESIGN-INC2 6.3), one sequence diagram per main use case (in the
increment that builds it), activity diagrams (Increments 2-3), survey lifecycle state machine (Increment 3),
data-flow diagram of the sentiment analysis (Increment 2).
