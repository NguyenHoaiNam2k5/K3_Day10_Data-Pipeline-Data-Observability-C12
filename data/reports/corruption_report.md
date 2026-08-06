# Data Corruption & Pipeline Repair Comparison Report

## Executive Summary
This report evaluates the impact of deliberate data corruption on RAG retrieval and answer quality, and verifies system recovery after repairing data from raw sources.

## 1. Performance Metrics Comparison
| State | Samples | Retrieval Hit Rate | Mean Token F1 | Judge Accuracy | Mean Judge Score |
| --- | --- | --- | --- | --- | --- |
| **Baseline** | 32 | 100.00% | 0.3292 | 28.12% | 2.06 |
| **Corrupted** | 32 | 50.00% | 0.1331 | 12.50% | 1.44 |
| **Repaired** | 32 | 100.00% | 0.3292 | 28.12% | 2.06 |

## 2. Data Quality & Observability Signals
| State | Quality Status | Freshness Status | Stale Rows | Quality Checks Passed |
| --- | --- | --- | --- | --- |
| **Corrupted** | `FAILED` | `STALE` | 3 | 3/6 |
| **Repaired** | `PASSED` | `FRESH` | 0 | 6/6 |

## 3. Analysis & Key Takeaways
1. **Impact of Corruption**: Deliberate injection of empty summaries, title truncation, date alterations, and missing records significantly reduced Retrieval Hit Rate and Judge Accuracy.
2. **Observability Detection**: Data Quality checks accurately flagged failing conditions (stale rows, empty titles/summaries, duplicate records).
3. **Pipeline Repair**: Re-ingesting and re-cleaning raw source records fully restored vector search retrieval hit rate and LLM response accuracy back to baseline levels.
