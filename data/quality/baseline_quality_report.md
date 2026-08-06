# Data Quality Report — baseline

## Dataset profile

| Field | Value |
| --- | --- |
| rows | 24 |
| columns | ['paper_id', 'title', 'summary', 'authors', 'categories', 'primary_category', 'published', 'updated', 'abs_url', 'pdf_url', 'comment', 'age_days', 'authors_joined', 'categories_joined', 'summary_chars', 'text_for_embedding'] |
| unique_paper_ids | 24 |

## Quality gates

Overall status: **PASS** (17/17 gates passed)

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
| source_reconciliation | PASS (raw_rows=24, clean_rows=24, clean_ids_not_in_raw_count=0) |
| evaluation_schema | PASS (missing_columns=[]) |
| evaluation_samples_complete | PASS (blank_count=0, samples=18) |
| evaluation_sample_id_unique | PASS (duplicate_count=0) |
| evaluation_ground_truth_ids_valid | PASS (ground_truth_doc_count=18, unknown_doc_id_count=0, covered_clean_doc_count=6) |

## Freshness

| Signal | Value |
| --- | --- |
| generated_at | 2026-08-06T04:33:54.692395+00:00 |
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

Generated at: 2026-08-06T04:33:54.675854+00:00. Values are read from the clean, raw and evaluation artifacts supplied to the quality check.
