# Baseline Data Pipeline Report (Phase 1)

## 1. Source Summary
- **Source API**: Crossref REST API
- **Query**: `agentic retrieval augmented generation large language model`
- **Fetched Records**: 24
- **Cleaned Records**: 24

## 2. Baseline Evaluation Metrics
| Metric | Value |
| --- | --- |
| Evaluation Samples | 32 |
| Retrieval Hit Rate | 100.00% |
| Mean Token F1 | 0.3292 |
| Judge Accuracy | 28.12% |
| Mean Judge Score | 2.06 / 5.0 |

## 3. Data Observability & Quality
- **Overall Quality Status**: `PASSED`
- **Freshness Status**: `FRESH`
- **Latest Publication Date**: 2026-08-01
- **Stale Rows Count**: 0

### Quality Checks Detail
| Check Name | Status | Details |
| --- | --- | --- |
| min_row_count | `PASSED` | Total rows = 24 (threshold >= 5) |
| paper_id_non_null | `PASSED` | Null paper_ids = 0 |
| paper_id_unique | `PASSED` | Duplicate paper_ids = 0 |
| title_validity | `PASSED` | Empty titles = 0 |
| summary_min_length | `PASSED` | Summaries < 20 chars = 0 |
| freshness_check | `PASSED` | Stale rows (> 180 days) = 0 |

## 4. Pipeline Conclusion
Phase 1 baseline pipeline successfully processed clean raw data, established vector index, and achieved baseline retrieval & LLM evaluation scores.
