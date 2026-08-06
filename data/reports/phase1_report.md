# Phase 1 Baseline Report

## Source and dataset

| Field | Value |
| --- | --- |
| source_api | Crossref REST API |
| source_query | agentic retrieval augmented generation large language model |
| fetched_records | 24 |
| cleaned_records | 24 |

## Evaluation metrics

| Metric | Value |
| --- | --- |
| samples | 18 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 0.7573 |
| judge_accuracy | 0.6667 |
| mean_judge_score | 4 |

## Data quality

Overall status: **PASS**

| Check | Result |
| --- | --- |
| schema | PASS (missing_columns=[]) |
| row_count | PASS (value=24, expected=> 0) |
| paper_id_complete | PASS (blank_count=0) |
| paper_id_unique | PASS (duplicate_id_count=0, duplicate_row_count=0) |
| title_complete | PASS (blank_count=0) |
| summary_complete | PASS (blank_count=0) |
| summary_min_length | PASS (min_chars=20, short_count=0) |
| summary_chars_consistent | PASS (mismatch_count=0) |
| embedding_text_complete | PASS (blank_count=0) |
| published_valid | PASS (invalid_count=0) |
| age_days_valid | PASS (invalid_count=0) |
| freshness | PASS (stale_rows=0, threshold_days=180) |
| source_reconciliation | SKIPPED (raw_records not provided) |
| evaluation_schema | SKIPPED (eval_set not provided) |

## Freshness

| Field | Value |
| --- | --- |
| generated_at | 2026-08-06T04:53:49.322771+00:00 |
| latest_published | 2026-08-01 |
| oldest_published | 2026-02-12 |
| min_age_days | 5 |
| max_age_days | 175 |
| stale_rows | 0 |
| invalid_published_rows | 0 |
| total_rows | 24 |
| freshness_threshold_days | 180 |
| is_fresh | PASS |

## Evidence

Metrics, quality and freshness values above are generated from the saved pipeline artifacts.
