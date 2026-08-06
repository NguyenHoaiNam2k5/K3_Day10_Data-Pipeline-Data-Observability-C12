# Data Quality Report — baseline_quality

## Dataset profile

| Field | Value |
| --- | --- |
| Rows | 24 |
| Columns | 16 |
| Unique paper IDs | 24 |
| Overall quality status | **PASS** |

The dataset contains the following columns: `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`, `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, and `text_for_embedding`.

## Quality gates

Overall status: **PASS**. All 12 executed checks passed; 2 optional checks were skipped because their input artifacts were not supplied to the quality checker.

| Check | Status | Evidence |
| --- | --- | --- |
| Schema | PASS | No required columns are missing |
| Row count | PASS | 24 rows; expected more than 0 |
| Paper ID completeness | PASS | 0 blank IDs |
| Paper ID uniqueness | PASS | 0 duplicate IDs and 0 duplicate rows |
| Title completeness | PASS | 0 blank titles |
| Summary completeness | PASS | 0 blank summaries |
| Summary minimum length | PASS | 0 summaries shorter than 20 characters |
| Summary character consistency | PASS | 0 mismatches between `summary_chars` and actual length |
| Embedding text completeness | PASS | 0 blank `text_for_embedding` values |
| Published date validity | PASS | 0 invalid publication dates |
| Age validity | PASS | 0 invalid or negative `age_days` values |
| Freshness | PASS | 0 stale rows at the 180-day threshold |
| Source reconciliation | SKIPPED | Raw records were not provided to this quality-check run |
| Evaluation schema | SKIPPED | Evaluation set was not provided to this quality-check run |

## Freshness

| Signal | Value |
| --- | --- |
| Latest publication date | 2026-08-01 |
| Oldest publication date | 2026-02-12 |
| Minimum age | 5 days |
| Maximum age | 175 days |
| Stale rows | 0 |
| Invalid publication dates | 0 |
| Total rows | 24 |
| Freshness threshold | 180 days |
| Overall freshness status | **PASS** |

All 24 records are within the configured 180-day freshness threshold. The oldest record is 175 days old, leaving a margin of 5 days before it would be classified as stale.

## Evidence and scope

This report is derived only from the following saved artifacts:

- `data/quality/baseline-quality_quality.json`, generated at `2026-08-06T04:53:49.317095+00:00`.
- `data/quality/freshness_report.json`, generated at `2026-08-06T04:53:49.322771+00:00`.

The available evidence supports dataset-level schema, completeness, uniqueness, validity, and freshness conclusions. It does not support raw-to-clean reconciliation or evaluation-set validation because those checks were skipped in the supplied baseline quality artifact.
