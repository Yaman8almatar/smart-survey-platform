# Graduation 1 diagrams (PlantUML)

These are the figures of the Graduation 1 report (Chapters 4, 5, 8, 9 and Appendix B), drawn from develop d127aa7.
They replace the Mermaid files in diagrams/ as the report's figures; the Mermaid files stay as the history of
TASK-46, TASK-59 and TASK-60.

- `src/`: PlantUML 1.2025.8 sources (47 diagrams and three include files: `style.iuml`, `er-head.iuml`, `cls-head.iuml`).
- `png/`: each source rendered at 150 dpi; each prints at 7.95 pt or more on A4 with 2.5 cm margins.
- `charts/`: three charts drawn with matplotlib, with no PlantUML source: `test-backend.png` from the pytest run of
  28 Nov 2026, `t2-headline.png` and `t2-confusion-m4.png` from evaluation/results/results.md.

Render one figure from this folder: `java -jar plantuml.jar -tpng -o ../png src/<name>.puml`.

Conventions: sequence diagrams use the teoz engine (`!pragma teoz true`) and draw UML activation bars; activity
guards are in square brackets; no figure draws its own title, because the report's numbered caption is the title;
a sequence diagram has at most five lifelines (actor, app or page, view, service, repositories with PostgreSQL).

| Figure | File | Caption |
|---|---|---|
| 4.1 | png/uc-respondent.png | Use case diagram: Respondent |
| 4.2 | png/uc-provider.png | Use case diagram: Service provider |
| 4.3 | png/uc-admin.png | Use case diagram: Admin |
| 4.4 | png/uc01-activity1.png | UC-01 (1 of 2) Register and confirm the email |
| 4.5 | png/uc01-activity2.png | UC-01 (2 of 2) Log in, or recover the password |
| 4.6 | png/uc04-activity1.png | UC-04 (1 of 2) Open the survey and resume |
| 4.7 | png/uc04-activity2.png | UC-04 (2 of 2) Answer and send |
| 4.8 | png/uc10-activity.png | UC-10 Define targeting and preview reach |
| 4.9 | png/uc11-activity1.png | UC-11 and UC-14 (1 of 2) Submit, review, publish |
| 4.10 | png/uc11-activity2.png | UC-11 (2 of 2) Pause, resume, close |
| 4.11 | png/fr04-activity1.png | FR-04 quality rules (1 of 2) Evidence to flags |
| 4.12 | png/fr04-activity2.png | FR-04 quality rules (2 of 2) Score, band and the provider's decision |
| 4.13 | png/worker-activity.png | T-9 and FR-05 analysis worker |
| 4.14 | png/uc01-seq1.png | UC-01 (1 of 4) Register in the app |
| 4.15 | png/uc01-seq2.png | UC-01 (2 of 4) Confirm the email address |
| 4.16 | png/uc01-seq3.png | UC-01 (3 of 4) Log in in the app |
| 4.17 | png/uc01-seq4.png | UC-01 (4 of 4) Recover the password |
| 4.18 | png/uc02-seq.png | UC-02 Manage demographic profile |
| 4.19 | png/uc03-seq.png | UC-03 Browse matching surveys |
| 4.20 | png/uc04-seq1.png | UC-04 (1 of 3) Open the survey and the draft |
| 4.21 | png/uc04-seq2.png | UC-04 (2 of 3) Answer and save the draft |
| 4.22 | png/uc04-seq3.png | UC-04 (3 of 3) Send the answers |
| 4.23 | png/uc06-seq.png | UC-06 View answered surveys |
| 4.24 | png/uc07-seq.png | UC-07 Register as provider and log in |
| 4.25 | png/uc08-seq1.png | UC-08 (1 of 2) Create and edit the survey |
| 4.26 | png/uc08-seq2.png | UC-08 (2 of 2) Add questions and attention checks |
| 4.27 | png/uc10-seq.png | UC-10 Define targeting and preview reach |
| 4.28 | png/uc11-seq1.png | UC-11 (1 of 2) Submit the survey for review |
| 4.29 | png/uc11-seq2.png | UC-11 (2 of 2) Pause, resume and close |
| 4.30 | png/uc12-seq1.png | UC-12 (1 of 3) Results, breakdown and filter |
| 4.31 | png/uc12-seq2.png | UC-12 (2 of 3) Responses one by one, include or exclude |
| 4.32 | png/uc12-seq3.png | UC-12 (3 of 3) Quality panel actions and analysis retry |
| 4.33 | png/uc13-seq.png | UC-13 Export results |
| 4.34 | png/uc14-seq.png | UC-14 Review survey |
| 4.35 | png/uc15-seq.png | UC-15 Manage users |
| 4.36 | png/uc16-seq.png | UC-16 View system reports |
| 4.37 | png/worker-seq.png | T-9 and FR-05 analysis worker, one batch |
| 5.1 | png/block-diagram.png | System block diagram: tiers, layers and processes |
| 5.2 | png/er1.png | ER view 1: accounts and profiles |
| 5.3 | png/er2.png | ER view 2: surveys, targeting and questions |
| 5.4 | png/er3.png | ER view 3: responses, quality and sentiment |
| 8.1 | charts/test-backend.png | Server test cases by test folder at commit d127aa7 (1,647, all passed) |
| 9.1 | charts/t2-headline.png | Headline macro-F1 of the candidates that cover both languages, with 95% bootstrap intervals |
| 9.2 | charts/t2-confusion-m4.png | Confusion matrices of the selected model M4 on the test set (rows: gold label) |
| B.1 | png/cls1.png | Class view 1: accounts and profiles |
| B.2 | png/cls2.png | Class view 2: surveys, targeting and questions |
| B.3 | png/cls3.png | Class view 3: responses, quality and sentiment |
| B.4 | png/dfd.png | DFD level 1: open answers to sentiment results (FR-05) |
| B.5 | png/state-survey.png | State machine of Survey.status (FR-11, FR-12) |
| B.6 | png/state-sentiment.png | State machine of SentimentAnalysisResult.status (T-9, FR-05) |
