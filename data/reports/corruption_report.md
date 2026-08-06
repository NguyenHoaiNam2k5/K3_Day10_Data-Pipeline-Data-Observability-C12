# Corruption and Repair Comparison Report

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired | Corrupted - baseline | Repaired - corrupted |
| --- | --- | --- | --- | --- | --- |
| retrieval_hit_rate | 1.0000 | 0.8333 | 1.0000 | -0.1667 | +0.1667 |
| mean_token_f1 | 0.7573 | 0.5178 | 0.7573 | -0.2395 | +0.2395 |
| judge_accuracy | 0.6667 | 0.5000 | 0.6667 | -0.1667 | +0.1667 |
| mean_judge_score | 4 | 3.3889 | 4 | -0.6111 | +0.6111 |

## Data quality

| Check | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| age_days_valid | PASS (invalid_count=0) | FAIL (invalid_count=4) | PASS (invalid_count=0) |
| embedding_text_complete | PASS (blank_count=0) | PASS (blank_count=0) | PASS (blank_count=0) |
| evaluation_schema | SKIPPED (eval_set not provided) | SKIPPED (eval_set not provided) | SKIPPED (eval_set not provided) |
| freshness | PASS (stale_rows=0, threshold_days=180) | FAIL (stale_rows=0, threshold_days=180) | PASS (stale_rows=0, threshold_days=180) |
| paper_id_complete | PASS (blank_count=0) | PASS (blank_count=0) | PASS (blank_count=0) |
| paper_id_unique | PASS (duplicate_id_count=0, duplicate_row_count=0) | FAIL (duplicate_id_count=3, duplicate_row_count=6) | PASS (duplicate_id_count=0, duplicate_row_count=0) |
| published_valid | PASS (invalid_count=0) | FAIL (invalid_count=4) | PASS (invalid_count=0) |
| row_count | PASS (value=24, expected=> 0) | PASS (value=23, expected=> 0) | PASS (value=24, expected=> 0) |
| schema | PASS (missing_columns=[]) | PASS (missing_columns=[]) | PASS (missing_columns=[]) |
| source_reconciliation | SKIPPED (raw_records not provided) | SKIPPED (raw_records not provided) | SKIPPED (raw_records not provided) |
| summary_chars_consistent | PASS (mismatch_count=0) | PASS (mismatch_count=0) | PASS (mismatch_count=0) |
| summary_complete | PASS (blank_count=0) | FAIL (blank_count=3) | PASS (blank_count=0) |
| summary_min_length | PASS (min_chars=20, short_count=0) | FAIL (min_chars=20, short_count=3) | PASS (min_chars=20, short_count=0) |
| title_complete | PASS (blank_count=0) | PASS (blank_count=0) | PASS (blank_count=0) |

## Freshness

| Signal | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| latest_published | 2026-08-01 | 2026-07-03 | 2026-08-01 |
| oldest_published | 2026-02-12 | 2026-02-12 | 2026-02-12 |
| stale_rows | 0 | 0 | 0 |
| total_rows | 24 | 23 | 24 |
| is_fresh | PASS | FAIL | PASS |

## Interpretation

Use the deltas and quality signals above to support conclusions; do not claim recovery unless repaired artifacts show it.
