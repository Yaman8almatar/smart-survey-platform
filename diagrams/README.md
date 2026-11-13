# Diagrams

Iteration 0 outputs (Agile Modeling: initial requirements and architecture envisioning), 2026-10-30, are PNG exports.
Increment 1 diagrams (2026-11-13, TASK-25) are Mermaid sources in Markdown files, which GitHub renders (D-141).
Each source file starts with a Basis block and ends with a legend table.

| Diagram | Source | Exports | Tool |
|---|---|---|---|
| Class diagram: 10 domain classes and their enumerations (Increment 1) | `class-diagram.md` | pending | Mermaid `classDiagram` |
| ER diagram: 10 tables, columns, keys and constraints table (Increment 1) | `erd.md` | pending | Mermaid `erDiagram` |
| Sequence diagram UC-02 Manage demographic profile (FR-02) | `sequence-uc02-profile.md` | pending | Mermaid `sequenceDiagram` |
| Sequence diagram UC-04 Answer a survey, draft and resume (FR-06) | `sequence-uc04-answer.md` | pending | Mermaid `sequenceDiagram` |
| Sequence diagram UC-06 View answered surveys (FR-01) | `sequence-uc06-answered.md` | pending | Mermaid `sequenceDiagram` |
| Initial class diagram: 9 domain classes (Iteration 0, 2026-10-30; kept as a record, superseded by `class-diagram.md`) | - | `class-diagram.png` | Mermaid |
| Use case diagrams: Respondent, Provider, Admin | - | `use-case-respondent.png`, `use-case-provider.png`, `use-case-admin.png` | UML 2.5 notation (preliminary) |

PNG exports of the Increment 1 diagrams for the report are pending; they are made later from the sources, outside
TASK-25.

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

## Planned in later increments
Drawn when the backlog item that needs them is pulled (Agile Modeling, model storming): the component diagram
(moved to Increment 2 with the analysis worker, DESIGN-INC2 6.3), one sequence diagram per main use case (in the
increment that builds it), activity diagrams (Increments 2-3), survey lifecycle state machine (Increment 3),
data-flow diagram of the sentiment analysis (Increment 2).
