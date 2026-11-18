# T-2 — Sentiment model evaluation protocol (NFR-07)

Version 1, frozen 2026-11-18 (TASK-37, D-161, D-162, D-172) **before any model sees a test item**.
This file is committed before the test set is built and before any model runs; the commit order on the branch is
the evidence (protocol → gold set → results). Any later change is a new protocol version with its own commit.

## 1. Purpose and scope

Choose the sentiment model for open answers (Modern Standard Arabic and English) from published models used as
they are. Nothing is trained or fine-tuned (D-004). NFR-07 requires that the chosen model's fine-tuning data is
documented and public, and that the model is measured on items that do **not** appear in that fine-tuning data.
The winner is wired into the analysis worker later, in FR-05; this task changes no backend, web or app code.

Dataset texts never enter the repository. The repository holds this protocol, the scripts that rebuild everything
from the public sources, item ids with SHA-256 hashes of the texts, predictions (labels and timings only) and results.
All data and models live under `C:\t2\` (not in git).

## 2. Candidates

| ID | Hub id | Covers | Status |
|---|---|---|---|
| M0 | cardiffnlp/twitter-roberta-base-sentiment-latest | English only | baseline (today's model); English rows only; cannot win |
| M1 | cardiffnlp/twitter-xlm-roberta-base-sentiment | ar, en | eligible |
| M2 | lxyuan/distilbert-base-multilingual-cased-sentiments-student | ar, en | eligible |
| M3 | tabularisai/multilingual-sentiment-analysis | ar, en | reference only: its training data is not public (NFR-07); cannot win |
| M4 | clapAI/roberta-base-multilingual-sentiment | ar, en | eligible |
| M5 | CAMeL-Lab/bert-base-arabic-camelbert-msa-sentiment | Arabic only | Arabic rows only; cannot win |
| R1 | router (see 2.1) | ar, en | eligible |

L1 (a paid LLM) is not run: no payment route (P-11); it would only be a reference row.

### 2.1 Router R1 (fixed now)

- Routing rule: the backend's language rule (`backend/services/text_language.py`): a text whose Arabic-range letters
  are at least half of its letters goes to the Arabic arm; every other text goes to the English arm.
- Arm pools: models whose fine-tuning data is public (NFR-07), i.e. every candidate except M3.
  Arabic arm from {M1, M2, M4, M5}; English arm from {M0, M1, M2, M4}.
- Pair choice, **on the development set only**: the Arabic arm is the pool member with the highest Arabic dev
  macro-F1, the English arm the one with the highest English dev macro-F1. Ties: lower dev p95 latency, then the
  lower candidate ID.
- R1's predictions are its arms' predictions on the routed items (no extra run); its per-item time is the arm's time;
  its weights are the sum of the two arms' weights; its peak memory is reported as the sum of the arms' peaks (an
  upper bound, both models resident); its licence is acceptable only if both arms' licences are.
- If both arms are the same model, R1 equals that model and is reported, but it is the same candidate.

## 3. Test sources (gold label = the source's own label, mapped)

| Pool | Language | Domain | Hub dataset (parquet export) | Rows used | Label map |
|---|---|---|---|---|---|
| en_reviews | English | reviews | SetFit/sst5, test split | all | 0, 1 negative; 2 neutral; 3, 4 positive |
| en_service | English | service | osanseviero/twitter-airline-sentiment, train split | `airline_sentiment_confidence` = 1.0 | the `airline_sentiment` value |
| ar_reviews | Arabic | reviews | mohamedadaly/labr, plain_text, test split, then train if a class falls short | label index 0 (1 star) and 4 (5 stars) only | 0 negative; 4 positive; no neutral |
| ar_posts | Arabic | posts | arbml/ArSarcasm_v2, test split, then train if a class falls short | `dialect` = "msa" and `label` = 0 (not sarcastic) | POS positive; NEG negative; NEU neutral |

No item is labelled, relabelled, rewritten or filtered by human or AI judgement (D-161). If a column named above
does not exist under that name in the export, the script stops; the mapping is not guessed.

### 3.1 Item filters (applied before the overlap filter and sampling, in this order)

1. 5 to 60 words (words = whitespace-separated tokens of the raw text).
2. No URL: the lower-cased text contains neither `http` nor `www.`.
3. Script: at least 90% of the letters (Unicode category L*) are in the language's script — the Arabic ranges of
   `text_language.py` (U+0600-06FF, U+0750-077F, U+08A0-08FF, U+FB50-FDFF, U+FE70-FEFF) for Arabic items; A-Z, a-z and
   U+00C0-024F for English items.
4. Duplicates by Normalisation A text (section 4) removed within each language, keeping the first in this order:
   pools in the table order above, splits test then train, rows in file order.

## 4. Overlap filter (fine-tuning corpora, Arabic and English rows only)

| Candidate | Hub dataset (parquet export) | Configs |
|---|---|---|
| M0 | cardiffnlp/tweet_eval | sentiment, all splits |
| M1 | cardiffnlp/tweet_sentiment_multilingual | arabic, english, all splits |
| M2 | tyqiangz/multilingual-sentiments | arabic, english, all splits |
| M4 | clapAI/MultiLingualSentiment | local main-revision parquet files, all splits, rows whose language column is "ar" or "en" (values checked first) |
| M5 | arbml/ASTD; arbml/ArSAS; cardiffnlp/tweet_sentiment_multilingual arabic (SemEval-2017 Arabic) | default; default; arabic |

M3's training data is not public, so no overlap check is possible for it; this is why it cannot win.

- **Normalisation A**: Unicode NFKC; remove URLs (`https?://\S+`, `www\.\S+`) and @mentions (`@\w+`); remove Arabic
  diacritics (U+064B-U+0652, U+0670) and tatweel (U+0640); lower-case Latin letters; collapse whitespace and strip.
- **Normalisation B**: A, then remove punctuation and symbols (Unicode categories P* and S*) and digits (category Nd),
  then collapse whitespace and strip.
- Hash = SHA-256 of the UTF-8 normalised text. One hash set per corpus holds the A-hashes and B-hashes of every row.
- A pool item is dropped when its A-hash or its B-hash is in the union of all corpus hash sets (so the test set is
  clean against every candidate, including both R1 arms). An empty B-text is never matched.
- Reported: per pool and per corpus, the number of filtered pool items that match; and per pool the total dropped.

## 5. Sampling (seed 20261118, `random.Random`)

One `random.Random(20261118)` instance is used for the whole of `sample.py`, in this order.

Cells and sizes (test + dev):

| Language | Pool | Class | Test | Dev |
|---|---|---|---|---|
| English | en_reviews | negative, neutral, positive | 25 each | 5 each |
| English | en_service | negative, neutral, positive | 25 each | 5 each |
| Arabic | ar_reviews | negative, positive | 25 each | 5 each |
| Arabic | ar_posts | negative, positive | 25 each | 5 each |
| Arabic | ar_posts | neutral | 50 | 10 |

Totals: test 150 per language (50 per class), dev 30 per language (10 per class).

For each cell in the table order (classes in the order negative, neutral, positive): the cell's candidates from the
test split are sorted by source id and shuffled; if the cell is ar_reviews or ar_posts and the test split holds fewer
than test + dev items, the train split's candidates for that class are sorted, shuffled and appended after them. The
first `test` items go to the test set and the next `dev` items to the dev set. A cell that cannot be filled keeps its
real size, is reported, and nothing is borrowed from another cell.

Ids: the whole test set is shuffled once more with the same generator and numbered `g1-0001`… in that order; the dev
set likewise `d1-0001`…. Ids therefore carry no label, domain or source information.

Audit: walking the test set in id order, the first 10 items of each (language, class) give 60 items. They are
written three times, to `C:\t2\audit\audit_yaman.csv`, `audit_hasan.csv` and `audit_yousef.csv`, columns
`id,text,label`, label blank, rows in id order, no source label anywhere. `evaluation/audit_ids.csv` lists the 60 ids.

## 6. Runs

- Laptop CPU, `torch.no_grad()`, `model.eval()`, one item at a time, truncation at 512 tokens.
- Each model runs in its own Python process, launched one after another in the foreground by `run_models.py`.
- M0 and M1 get their model cards' preprocessing: a whitespace token starting with `@` (longer than 1) becomes
  `@user`, one starting with `http` becomes `http`. Other models get the raw text.
- Labels come from each config's `id2label`, lower-cased, mapped to negative, neutral, positive. M3: very negative
  and negative → negative; neutral → neutral; positive and very positive → positive. An unknown label stops the run.
- M0 runs on English items only, M5 on Arabic items only, the others on all items; dev and test.
- Recorded per item: predicted label, milliseconds (tokenise plus forward, `time.perf_counter`). Per model: load
  seconds (tokenizer plus model), peak resident memory (psutil; on Windows the process peak working set), weights
  file size on disk.

## 7. Metrics

Per model and language, on the test set: macro-F1 over the three classes (primary), per-class precision, recall and
F1, neutral recall, accuracy, the 3 × 3 confusion matrix, and a 95% percentile interval of macro-F1 from 2,000
bootstrap resamples of the items (numpy `default_rng(20261118)`). A class with no predictions has precision 0.

Headline = mean of Arabic and English macro-F1, for models that cover both (M1, M2, M3, M4, R1). Its interval comes
from resampling the Arabic and the English items independently in each of the 2,000 rounds.

Latency: p50 and p95 of the per-item milliseconds over the model's test items.

## 8. Decision rule (fixed before any run)

1. **Eligibility.** Only M1, M2, M4 and R1 can win, and only with test predictions for every test item. M0, M3 and
   M5 are reported in their own rows and cannot win.
2. **Leader.** The eligible candidate with the highest headline.
3. **Ties.** For each other eligible candidate, a paired bootstrap (2,000 rounds, numpy `default_rng(20261118)`,
   the same resampled items for both models in each round, Arabic and English resampled independently) gives a 95%
   percentile interval of headline(rival) − headline(leader). If the interval includes zero, the rival is tied with
   the leader.
4. **Tie-breaks**, applied in order to the leader and its tied rivals until one remains:
   a. a licence declared on the model card with no non-commercial clause (a card that declares no licence does not
      pass this step; R1 passes only if both arms pass);
   b. higher mean neutral recall (mean of Arabic and English);
   c. lower p95 latency;
   d. smaller weights on disk.
   A step that every remaining candidate passes or fails equally does not remove anyone.
5. `results.md` names the winner and the rule step that decided it (2 if nobody is tied, otherwise the tie-break
   step that left one candidate).

## 9. Steps, in order

1. Commit this protocol and LEAKAGE.md (no data fetched, no model run).
2. `fetch_data.py` — download the public datasets (parquet export) into `C:\t2\data\raw\`.
3. `build_pools.py` — sources, label maps, filters → `C:\t2\data\pools.parquet`.
4. `overlap_filter.py` — corpus hash sets, drop counts → `C:\t2\data\pools_clean.parquet`, `results/overlap.csv`.
5. `sample.py` — test, dev, audit files; the id files are committed with the SHA-256 of `gold_v1_ids.csv` in the
   commit message. No model runs before this commit.
6. `run_models.py` — dev and test runs of M0-M5, then R1 (pair from dev only).
7. `metrics.py` — `results/results.csv` and `results/results.md`, including the winner.
8. `audit_agreement.py` — after the members fill the audit files: Fleiss' kappa and each member's agreement with the
   source labels (`results/audit.md`).

## 10. Limits (stated in advance)

- Reviews and short posts are not survey answers; the domain gap to the platform's open answers is not measured.
- Star ratings are weak labels; they are reduced to 1 and 5 stars to keep only the clear cases, so the Arabic
  review items have no neutral class.
- Dialectal Arabic is not measured (D-054): Arabic posts are restricted to the MSA rows of ArSarcasm v2.
- 150 items per language give a macro-F1 interval of about ±0.07; small differences between models will be ties.
- The overlap clause covers documented fine-tuning data only; pretraining corpora (for example the ~124M and ~198M
  tweets of M0 and M1) are outside the clause and are not checked.
- The overlap filter catches exact and near-exact copies (after normalisation), not paraphrases.
- The source labels are taken as gold; the three-member audit (section 5) measures how far they can be trusted.
