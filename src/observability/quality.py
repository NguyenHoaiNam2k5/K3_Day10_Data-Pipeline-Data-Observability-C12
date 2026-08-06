from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings


from typing import Any
from pathlib import Path
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    total_rows = len(df)
    checks: list[dict[str, Any]] = []

    # Check 1: Row count
    row_count_passed = total_rows >= 5
    checks.append(
        {
            "name": "min_row_count",
            "passed": row_count_passed,
            "details": f"Total rows = {total_rows} (threshold >= 5)",
        }
    )

    # Check 2: Paper ID non-null
    id_null_count = int(df["paper_id"].isnull().sum()) if not df.empty else 0
    checks.append(
        {
            "name": "paper_id_non_null",
            "passed": id_null_count == 0,
            "details": f"Null paper_ids = {id_null_count}",
        }
    )

    # Check 3: Paper ID unique
    id_unique_passed = bool(df["paper_id"].is_unique) if not df.empty else True
    duplicate_count = total_rows - len(df["paper_id"].unique()) if not df.empty else 0
    checks.append(
        {
            "name": "paper_id_unique",
            "passed": id_unique_passed,
            "details": f"Duplicate paper_ids = {duplicate_count}",
        }
    )

    # Check 4: Title valid
    empty_titles = int((df["title"].str.strip() == "").sum()) if not df.empty else 0
    checks.append(
        {
            "name": "title_validity",
            "passed": empty_titles == 0,
            "details": f"Empty titles = {empty_titles}",
        }
    )

    # Check 5: Summary length
    short_summaries = int((df["summary"].str.len() < 20).sum()) if not df.empty else 0
    checks.append(
        {
            "name": "summary_min_length",
            "passed": short_summaries == 0,
            "details": f"Summaries < 20 chars = {short_summaries}",
        }
    )

    # Check 6: Freshness age_days
    stale_count = int((df["age_days"] > settings.freshness_threshold_days).sum()) if not df.empty else 0
    checks.append(
        {
            "name": "freshness_check",
            "passed": stale_count == 0,
            "details": f"Stale rows (> {settings.freshness_threshold_days} days) = {stale_count}",
        }
    )

    all_passed = all(c["passed"] for c in checks)

    result = {
        "report_name": report_name,
        "total_rows": total_rows,
        "all_passed": all_passed,
        "checks": checks,
    }

    out_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(out_path, result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    if df.empty:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": True,
            "threshold_days": settings.freshness_threshold_days,
        }
        write_json(Path(report_path), report)
        return report

    latest_published = str(df["published"].max())
    oldest_published = str(df["published"].min())
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    is_fresh = stale_rows == 0

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh,
        "threshold_days": settings.freshness_threshold_days,
    }

    write_json(Path(report_path), report)
    return report

