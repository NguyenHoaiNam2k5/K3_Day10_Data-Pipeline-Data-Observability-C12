from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, safe_slug, write_json


def _blank_count(df: pd.DataFrame, column: str) -> int:
    if column not in df:
        return len(df)
    return int(df[column].fillna("").astype(str).str.strip().eq("").sum())


def _freshness_values(df: pd.DataFrame, settings: Settings) -> tuple[pd.Series, pd.Series, int, int]:
    if "published" not in df:
        empty = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
        return empty, pd.Series(float("nan"), index=df.index), 0, len(df)

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    age_days = pd.to_numeric(df.get("age_days"), errors="coerce")
    computed_age = (pd.Timestamp(now_utc()) - published).dt.days
    age_days = age_days.fillna(computed_age)
    invalid_dates = int(published.isna().sum())
    stale_rows = int((age_days > settings.freshness_threshold_days).sum())
    return published, age_days, stale_rows, invalid_dates


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run auditable completeness, uniqueness, validity and freshness checks."""
    required = ["paper_id", "title", "summary", "published", "text_for_embedding"]
    missing_columns = [column for column in required if column not in df]
    paper_ids = df["paper_id"].fillna("").astype(str).str.strip() if "paper_id" in df else pd.Series("", index=df.index)
    duplicate_rows = paper_ids[paper_ids.duplicated(keep=False) & paper_ids.ne("")]
    published, age_days, stale_rows, invalid_dates = _freshness_values(df, settings)
    summary_length = df["summary"].fillna("").astype(str).str.len() if "summary" in df else pd.Series(0, index=df.index)

    checks = {
        "schema": {"passed": not missing_columns, "missing_columns": missing_columns},
        "row_count": {"passed": len(df) > 0, "value": len(df), "expected": "> 0"},
        "paper_id_complete": {"passed": _blank_count(df, "paper_id") == 0, "blank_count": _blank_count(df, "paper_id")},
        "paper_id_unique": {
            "passed": duplicate_rows.empty,
            "duplicate_id_count": int(duplicate_rows.nunique()),
            "duplicate_row_count": int(len(duplicate_rows)),
        },
        "title_complete": {"passed": _blank_count(df, "title") == 0, "blank_count": _blank_count(df, "title")},
        "summary_complete": {"passed": _blank_count(df, "summary") == 0, "blank_count": _blank_count(df, "summary")},
        "summary_min_length": {"passed": int((summary_length < 20).sum()) == 0, "min_chars": 20, "short_count": int((summary_length < 20).sum())},
        "embedding_text_complete": {
            "passed": _blank_count(df, "text_for_embedding") == 0,
            "blank_count": _blank_count(df, "text_for_embedding"),
        },
        "published_valid": {"passed": invalid_dates == 0, "invalid_count": invalid_dates},
        "freshness": {
            "passed": stale_rows == 0 and invalid_dates == 0,
            "stale_rows": stale_rows,
            "threshold_days": settings.freshness_threshold_days,
        },
    }
    result = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "total_rows": len(df),
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{safe_slug(report_name)}_quality.json", result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication recency without mutating the input dataframe."""
    published, _, stale_rows, invalid_dates = _freshness_values(df, settings)
    valid_dates = published.dropna()
    result = {
        "generated_at": now_utc().isoformat(),
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "invalid_published_rows": invalid_dates,
        "total_rows": len(df),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": len(df) > 0 and stale_rows == 0 and invalid_dates == 0,
    }
    write_json(report_path, result)
    return result
