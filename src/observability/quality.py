from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, safe_slug, write_json


REQUIRED_COLUMNS = ("paper_id", "title", "summary", "published", "text_for_embedding")
EVAL_COLUMNS = ("id", "question", "ground_truth", "ground_truth_doc_ids", "question_type")


def _text(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column].fillna("").astype(str).str.strip() if column in df else pd.Series("", index=df.index)


def _freshness_values(df: pd.DataFrame, settings: Settings) -> tuple[pd.Series, pd.Series, int, int]:
    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True)
    if not isinstance(published, pd.Series):
        published = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    age_days = pd.to_numeric(df.get("age_days"), errors="coerce")
    if not isinstance(age_days, pd.Series):
        age_days = pd.Series(float("nan"), index=df.index)
    age_days = age_days.fillna((pd.Timestamp(now_utc()) - published).dt.days)
    invalid_dates = int(published.isna().sum())
    return published, age_days, int((age_days > settings.freshness_threshold_days).sum()), invalid_dates


def _source_check(df: pd.DataFrame, raw_records: pd.DataFrame | None) -> dict[str, Any]:
    if raw_records is None:
        return {"passed": True, "status": "SKIPPED", "reason": "raw_records not provided"}
    raw_ids = set(_text(raw_records, "paper_id")) - {""}
    clean_ids = set(_text(df, "paper_id")) - {""}
    missing = clean_ids - raw_ids
    return {
        "passed": not missing,
        "raw_rows": len(raw_records),
        "clean_rows": len(df),
        "clean_ids_not_in_raw_count": len(missing),
    }


def _evaluation_checks(df: pd.DataFrame, eval_set: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if eval_set is None:
        return {"evaluation_schema": {"passed": True, "status": "SKIPPED", "reason": "eval_set not provided"}}
    missing_columns = [column for column in EVAL_COLUMNS if column not in eval_set]
    sample_ids = _text(eval_set, "id")
    required_blank_count = sum(int(_text(eval_set, column).eq("").sum()) for column in ("id", "question", "ground_truth", "question_type"))
    doc_ids = eval_set.get("ground_truth_doc_ids", pd.Series([], dtype=object)).explode().dropna().astype(str).str.strip()
    valid_docs = set(_text(df, "paper_id")) - {""}
    unknown_docs = set(doc_ids) - valid_docs - {""}
    return {
        "evaluation_schema": {"passed": not missing_columns, "missing_columns": missing_columns},
        "evaluation_samples_complete": {"passed": required_blank_count == 0, "blank_count": required_blank_count, "samples": len(eval_set)},
        "evaluation_sample_id_unique": {"passed": bool(sample_ids[sample_ids.ne("")].is_unique), "duplicate_count": int(sample_ids.duplicated().sum())},
        "evaluation_ground_truth_ids_valid": {
            "passed": bool(len(doc_ids)) and not unknown_docs,
            "ground_truth_doc_count": int(len(doc_ids)),
            "unknown_doc_id_count": len(unknown_docs),
            "covered_clean_doc_count": int(doc_ids.nunique()),
        },
    }


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
    *,
    raw_records: pd.DataFrame | None = None,
    eval_set: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Validate clean data and optional source/evaluation artifacts; save auditable JSON."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df]
    paper_ids, titles, summaries, embedding_text = (_text(df, column) for column in ("paper_id", "title", "summary", "text_for_embedding"))
    published, age_days, stale_rows, invalid_dates = _freshness_values(df, settings)
    duplicate_ids = paper_ids[paper_ids.ne("") & paper_ids.duplicated(keep=False)]
    summary_length = summaries.str.len()
    summary_chars = pd.to_numeric(df.get("summary_chars"), errors="coerce")
    summary_chars_mismatch = int((summary_chars.notna() & summary_chars.ne(summary_length)).sum()) if isinstance(summary_chars, pd.Series) else 0
    checks = {
        "schema": {"passed": not missing_columns, "missing_columns": missing_columns},
        "row_count": {"passed": len(df) > 0, "value": len(df), "expected": "> 0"},
        "paper_id_complete": {"passed": bool(paper_ids.ne("").all()), "blank_count": int(paper_ids.eq("").sum())},
        "paper_id_unique": {"passed": duplicate_ids.empty, "duplicate_id_count": int(duplicate_ids.nunique()), "duplicate_row_count": len(duplicate_ids)},
        "title_complete": {"passed": bool(titles.ne("").all()), "blank_count": int(titles.eq("").sum())},
        "summary_complete": {"passed": bool(summaries.ne("").all()), "blank_count": int(summaries.eq("").sum())},
        "summary_min_length": {"passed": bool((summary_length >= 20).all()), "min_chars": 20, "short_count": int((summary_length < 20).sum())},
        "summary_chars_consistent": {"passed": summary_chars_mismatch == 0, "mismatch_count": summary_chars_mismatch},
        "embedding_text_complete": {"passed": bool(embedding_text.ne("").all()), "blank_count": int(embedding_text.eq("").sum())},
        "published_valid": {"passed": invalid_dates == 0, "invalid_count": invalid_dates},
        "age_days_valid": {"passed": bool(age_days.notna().all() and (age_days >= 0).all()), "invalid_count": int(age_days.isna().sum() + (age_days < 0).sum())},
        "freshness": {"passed": stale_rows == 0 and invalid_dates == 0, "stale_rows": stale_rows, "threshold_days": settings.freshness_threshold_days},
        "source_reconciliation": _source_check(df, raw_records),
        **_evaluation_checks(df, eval_set),
    }
    result = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "dataset": {"rows": len(df), "columns": list(df.columns), "unique_paper_ids": int(paper_ids[paper_ids.ne("")].nunique())},
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{safe_slug(report_name)}_quality.json", result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication recency without mutating the input dataframe."""
    published, age_days, stale_rows, invalid_dates = _freshness_values(df, settings)
    valid_dates = published.dropna()
    result = {
        "generated_at": now_utc().isoformat(),
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "min_age_days": int(age_days.min()) if age_days.notna().any() else None,
        "max_age_days": int(age_days.max()) if age_days.notna().any() else None,
        "stale_rows": stale_rows,
        "invalid_published_rows": invalid_dates,
        "total_rows": len(df),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": len(df) > 0 and stale_rows == 0 and invalid_dates == 0,
    }
    write_json(report_path, result)
    return result
