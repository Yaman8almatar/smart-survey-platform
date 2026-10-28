# Diagrams

Iteration 0 outputs (Agile Modeling: initial requirements and architecture envisioning), 2026-10-30.
The diagrams are PNG exports.

| Diagram | Source | Exports | Tool |
|---|---|---|---|
| Initial class diagram: 9 domain classes | - | `class-diagram.png` | Mermaid |
| Use case diagrams: Respondent, Provider, Admin | - | `use-case-respondent.png`, `use-case-provider.png`, `use-case-admin.png` | UML 2.5 notation (preliminary) |

The architecture diagram is on slide 9 of the Seminar 1 deck in documentation/graduation-1/.

## Rules
- Architecture: tiers Client / Application / Data; layers Presentation / Business / Data Source
  (Fowler, Patterns of Enterprise Application Architecture, Ch. 1). The Data Source layer holds the repositories
  and the gateway to the external sentiment service. Service Layer, Repository, Active Record and Gateway are
  patterns, not layers.
- Use cases are drawn at user-goal level: no "Log in" use case and no include or extend relations
  (Larman, Applying UML and Patterns, 2nd ed., Ch. 6).
- Requirement IDs are those of the Product Backlog: FR-01..FR-20 for Graduation 1.

## Planned in later sprints
ERD with relational schema and constraints (Sprint 1), component diagram (Sprint 1), one sequence diagram per
main use case (in the sprint that builds it), activity diagrams (Sprints 2-3), survey lifecycle state machine
(Sprint 3), data-flow diagram of the sentiment analysis (Sprint 2).
