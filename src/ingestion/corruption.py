from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_SEED = 42


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy/datetime values to JSON-safe Python values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, datetime):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def _fraction_to_count(total: int, fraction: float) -> int:
    """Convert fraction to count. fraction=0 means no corruption."""
    if total <= 0 or fraction <= 0:
        return 0

    if fraction > 1:
        raise ValueError("Corruption fraction must be between 0 and 1.")

    return min(total, max(1, round(total * fraction)))


def _take_indices(pool: list[int], count: int) -> list[int]:
    """Take indices from a shuffled pool without replacement."""
    taken = pool[:count]
    del pool[:count]
    return taken


def _build_text_for_embedding(row: pd.Series) -> str:
    """Rebuild embedding text from currently available fields."""
    parts = [
        str(row.get("title", "") or "").strip(),
        str(row.get("summary", "") or "").strip(),
        str(row.get("authors_joined", "") or "").strip(),
        str(row.get("categories_joined", "") or "").strip(),
        str(row.get("primary_category", "") or "").strip(),
    ]

    return "\n".join(part for part in parts if part)


def _inject_destructive_noise(text: str, rng: random.Random) -> str:
    """Damage semantic content instead of only appending harmless noise."""
    words = str(text or "").split()

    noise = [
        "xqz9283",
        "malformed_metadata",
        "corrupted_fragment",
        "unknown_unknown_unknown",
        "[BROKEN_TEXT]",
    ]

    if len(words) < 8:
        return " ".join(rng.sample(noise, k=3))

    cut_start = len(words) // 3
    cut_size = max(3, len(words) // 3)
    cut_end = min(len(words), cut_start + cut_size)

    damaged = words[:cut_start] + rng.sample(noise, k=3) + words[cut_end:]
    return " ".join(damaged)


def _resolve_reference_date(
    df: pd.DataFrame,
    run_date: datetime | str | None,
) -> pd.Timestamp:
    """Resolve deterministic reference date for age_days."""
    if run_date is not None:
        reference = pd.Timestamp(run_date)

        if reference.tzinfo is None:
            reference = reference.tz_localize("UTC")
        else:
            reference = reference.tz_convert("UTC")

        return reference.normalize()

    if "published" in df.columns and "age_days" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True)
        age_days = pd.to_numeric(df["age_days"], errors="coerce")
        inferred = (published + pd.to_timedelta(age_days, unit="D")).dropna()

        if not inferred.empty:
            return inferred.median().normalize()

    return pd.Timestamp.now(tz="UTC").normalize()


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: str | Path,
    *,
    run_date: datetime | str | None = None,
    seed: int = DEFAULT_SEED,
    drop_latest_fraction: float = 0.15,
    blank_summary_fraction: float = 0.15,
    noise_fraction: float = 0.20,
    truncate_title_fraction: float = 0.15,
    stale_date_fraction: float = 0.20,
    duplicate_fraction: float = 0.15,
    allow_overlap: bool = False,
) -> pd.DataFrame:
    """Create a corrupted copy of a clean dataframe.

    This function simulates realistic data incidents:
    - latest records missing
    - blank summaries
    - noisy semantic text
    - damaged titles
    - stale publication dates
    - duplicate rows

    It never mutates the original dataframe.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    required_columns = {
        "paper_id",
        "title",
        "summary",
        "published",
    }

    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns for corruption: {sorted(missing_columns)}"
        )

    rng = random.Random(seed)
    reference_date = _resolve_reference_date(df, run_date)

    corrupted = df.copy(deep=True).reset_index(drop=True)

    log: dict[str, Any] = {
        "seed": seed,
        "run_date": reference_date.isoformat(),
        "allow_overlap": allow_overlap,
        "source_row_count": int(len(corrupted)),
        "result_row_count": None,
        "operations": {},
        "validation": {},
    }

    # 1. Drop latest records
    published_dates = pd.to_datetime(
        corrupted["published"],
        errors="coerce",
        utc=True,
    )

    latest_indices = (
        published_dates.dropna()
        .sort_values(ascending=False)
        .index
        .astype(int)
        .tolist()
    )

    drop_count = _fraction_to_count(
        len(latest_indices),
        drop_latest_fraction,
    )

    drop_indices = latest_indices[:drop_count]

    dropped_records = []
    for index in drop_indices:
        dropped_records.append(
            {
                "paper_id": _json_safe(corrupted.at[index, "paper_id"]),
                "title": _json_safe(corrupted.at[index, "title"]),
                "published": _json_safe(corrupted.at[index, "published"]),
            }
        )

    corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)

    log["operations"]["drop_latest_records"] = {
        "count": len(dropped_records),
        "records": dropped_records,
    }

    # 2. Prepare corruption groups
    candidate_indices = list(corrupted.index)
    rng.shuffle(candidate_indices)

    blank_count = _fraction_to_count(len(corrupted), blank_summary_fraction)
    noise_count = _fraction_to_count(len(corrupted), noise_fraction)
    title_count = _fraction_to_count(len(corrupted), truncate_title_fraction)
    stale_count = _fraction_to_count(len(corrupted), stale_date_fraction)

    if allow_overlap:
        blank_indices = rng.sample(list(corrupted.index), blank_count)
        noise_indices = rng.sample(list(corrupted.index), noise_count)
        title_indices = rng.sample(list(corrupted.index), title_count)
        stale_indices = rng.sample(list(corrupted.index), stale_count)
    else:
        total_needed = blank_count + noise_count + title_count + stale_count

        if total_needed > len(candidate_indices):
            raise ValueError(
                "Non-overlapping corruption groups exceed dataframe size. "
                "Reduce fractions or set allow_overlap=True."
            )

        blank_indices = _take_indices(candidate_indices, blank_count)
        noise_indices = _take_indices(candidate_indices, noise_count)
        title_indices = _take_indices(candidate_indices, title_count)
        stale_indices = _take_indices(candidate_indices, stale_count)

    # 3. Blank summaries
    blank_changes = []

    for index in blank_indices:
        old_summary = str(corrupted.at[index, "summary"] or "")
        corrupted.at[index, "summary"] = ""

        blank_changes.append(
            {
                "paper_id": _json_safe(corrupted.at[index, "paper_id"]),
                "before": {"summary_chars": len(old_summary)},
                "after": {"summary_chars": 0},
            }
        )

    log["operations"]["blank_summary"] = {
        "count": len(blank_changes),
        "records": blank_changes,
    }

    # 4. Inject destructive noise
    noise_changes = []

    for index in noise_indices:
        old_summary = str(corrupted.at[index, "summary"] or "")
        new_summary = _inject_destructive_noise(old_summary, rng)

        corrupted.at[index, "summary"] = new_summary

        noise_changes.append(
            {
                "paper_id": _json_safe(corrupted.at[index, "paper_id"]),
                "before": {
                    "summary_chars": len(old_summary),
                    "preview": old_summary[:120],
                },
                "after": {
                    "summary_chars": len(new_summary),
                    "preview": new_summary[:120],
                },
            }
        )

    log["operations"]["inject_summary_noise"] = {
        "count": len(noise_changes),
        "records": noise_changes,
    }

    # 5. Truncate or damage titles
    title_changes = []

    for index in title_indices:
        old_title = str(corrupted.at[index, "title"] or "")
        words = old_title.split()

        if len(words) >= 3:
            new_title = " ".join(words[:2])
        elif len(old_title) > 8:
            new_title = old_title[:5].rstrip()
        else:
            new_title = f"Untitled {rng.randint(1000, 9999)}"

        corrupted.at[index, "title"] = new_title

        title_changes.append(
            {
                "paper_id": _json_safe(corrupted.at[index, "paper_id"]),
                "before": {"title": old_title},
                "after": {"title": new_title},
            }
        )

    log["operations"]["truncate_title"] = {
        "count": len(title_changes),
        "records": title_changes,
    }

    # 6. Make publication dates stale
    stale_changes = []

    for index in stale_indices:
        old_published = corrupted.at[index, "published"]
        parsed = pd.to_datetime(old_published, errors="coerce", utc=True)

        if pd.isna(parsed):
            continue

        years_subtracted = rng.choice([5, 8, 10, 15])
        new_published = parsed - pd.DateOffset(years=years_subtracted)

        corrupted.at[index, "published"] = new_published.isoformat()

        stale_changes.append(
            {
                "paper_id": _json_safe(corrupted.at[index, "paper_id"]),
                "before": {"published": _json_safe(old_published)},
                "after": {"published": new_published.isoformat()},
                "years_subtracted": years_subtracted,
            }
        )

    log["operations"]["stale_published_date"] = {
        "count": len(stale_changes),
        "records": stale_changes,
    }

    # 7. Add duplicate rows
    duplicate_count = _fraction_to_count(len(corrupted), duplicate_fraction)

    duplicate_indices = (
        rng.sample(list(corrupted.index), duplicate_count)
        if duplicate_count > 0
        else []
    )

    duplicate_rows = corrupted.loc[duplicate_indices].copy()

    duplicate_records = []
    for index in duplicate_indices:
        duplicate_records.append(
            {
                "paper_id": _json_safe(corrupted.at[index, "paper_id"]),
                "title": _json_safe(corrupted.at[index, "title"]),
            }
        )

    if not duplicate_rows.empty:
        corrupted = pd.concat(
            [corrupted, duplicate_rows],
            ignore_index=True,
        )

    log["operations"]["add_duplicate_rows"] = {
        "count": len(duplicate_records),
        "records": duplicate_records,
    }

    # 8. Rebuild helper fields
    corrupted["summary"] = corrupted["summary"].fillna("").astype(str)
    corrupted["title"] = corrupted["title"].fillna("").astype(str)

    corrupted["summary_chars"] = corrupted["summary"].str.len()

    parsed_published = pd.to_datetime(
        corrupted["published"],
        errors="coerce",
        utc=True,
    )

    corrupted["age_days"] = (reference_date - parsed_published).dt.days

    corrupted["text_for_embedding"] = corrupted.apply(
        _build_text_for_embedding,
        axis=1,
    )

    # 9. Validation summary
    duplicate_paper_ids = int(
        corrupted["paper_id"].duplicated(keep=False).sum()
    )

    blank_summaries = int(
        corrupted["summary"].fillna("").astype(str).str.strip().eq("").sum()
    )

    stale_rows = int(
        pd.to_numeric(corrupted["age_days"], errors="coerce").gt(180).sum()
    )

    empty_embedding_texts = int(
        corrupted["text_for_embedding"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    log["result_row_count"] = int(len(corrupted))
    log["validation"] = {
        "duplicate_paper_id_rows": duplicate_paper_ids,
        "blank_summaries": blank_summaries,
        "stale_rows_age_days_gt_180": stale_rows,
        "empty_text_for_embedding": empty_embedding_texts,
    }

    # 10. Write log
    output_path = Path(output_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(log, file, ensure_ascii=False, indent=2)

    return corrupted


# ---------------------------------------------------------------------
# Real Data Tests & Demonstration
# Run:
#   python src/ingestion/corruption.py
# ---------------------------------------------------------------------


def _load_real_clean_dataframe(data_dir: str | Path = "data") -> pd.DataFrame:
    """Load real clean dataframe from data/clean or build from data/raw/crossref_records.json."""
    base = Path(data_dir)
    clean_json = base / "clean" / "papers_clean.json"
    clean_csv = base / "clean" / "papers_clean.csv"
    raw_json = base / "raw" / "crossref_records.json"

    if clean_json.exists() and clean_json.stat().st_size > 0:
        return pd.read_json(clean_json)
    if clean_csv.exists() and clean_csv.stat().st_size > 0:
        return pd.read_csv(clean_csv)
    if raw_json.exists() and raw_json.stat().st_size > 0:
        from core.utils import read_json
        from ingestion.cleaning import build_clean_dataframe
        from ingestion.crossref import PaperRecord

        raw_data = read_json(raw_json)
        records = [PaperRecord(**item) for item in raw_data]
        return build_clean_dataframe(records, datetime.now(timezone.utc))

    raise FileNotFoundError(
        f"No real data found in {clean_json}, {clean_csv}, or {raw_json}."
    )


def _assert_original_not_mutated(
    original: pd.DataFrame,
    snapshot: pd.DataFrame,
) -> None:
    pd.testing.assert_frame_equal(original, snapshot)


def _test_corruption_basic() -> None:
    df = _load_real_clean_dataframe()
    snapshot = df.copy(deep=True)

    log_path = Path("data/results/real_corruption_log.json")

    corrupted = corrupt_clean_dataframe(
        df,
        log_path,
        run_date="2026-08-06T00:00:00Z",
        seed=42,
    )

    assert log_path.exists(), "Log file was not created."
    assert len(corrupted) > 0, "Corrupted dataframe is empty."
    assert "text_for_embedding" in corrupted.columns
    assert "summary_chars" in corrupted.columns
    assert "age_days" in corrupted.columns

    _assert_original_not_mutated(df, snapshot)

    log = json.loads(log_path.read_text(encoding="utf-8"))

    assert log["seed"] == 42
    assert log["source_row_count"] == len(df)
    assert log["result_row_count"] == len(corrupted)

    required_operations = {
        "drop_latest_records",
        "blank_summary",
        "inject_summary_noise",
        "truncate_title",
        "stale_published_date",
        "add_duplicate_rows",
    }

    assert required_operations.issubset(log["operations"].keys())

    assert log["operations"]["drop_latest_records"]["count"] > 0
    assert log["operations"]["blank_summary"]["count"] > 0
    assert log["operations"]["inject_summary_noise"]["count"] > 0
    assert log["operations"]["truncate_title"]["count"] > 0
    assert log["operations"]["stale_published_date"]["count"] > 0
    assert log["operations"]["add_duplicate_rows"]["count"] > 0

    assert log["validation"]["duplicate_paper_id_rows"] > 0
    assert log["validation"]["blank_summaries"] > 0

    print("PASS: basic corruption test on real dataset")


def _test_reproducibility() -> None:
    df = _load_real_clean_dataframe()

    first = corrupt_clean_dataframe(
        df,
        "data/results/real_corruption_log_first.json",
        run_date="2026-08-06T00:00:00Z",
        seed=42,
    )

    second = corrupt_clean_dataframe(
        df,
        "data/results/real_corruption_log_second.json",
        run_date="2026-08-06T00:00:00Z",
        seed=42,
    )

    pd.testing.assert_frame_equal(first, second)

    print("PASS: reproducibility test on real dataset")


def _test_zero_fraction_no_change_except_rebuild() -> None:
    df = _load_real_clean_dataframe()
    snapshot = df.copy(deep=True)

    corrupted = corrupt_clean_dataframe(
        df,
        "data/results/real_corruption_log_zero.json",
        run_date="2026-08-06T00:00:00Z",
        seed=42,
        drop_latest_fraction=0,
        blank_summary_fraction=0,
        noise_fraction=0,
        truncate_title_fraction=0,
        stale_date_fraction=0,
        duplicate_fraction=0,
    )

    assert len(corrupted) == len(df)
    assert corrupted["paper_id"].tolist() == df["paper_id"].tolist()
    assert corrupted["title"].tolist() == df["title"].tolist()
    assert corrupted["summary"].tolist() == df["summary"].tolist()
    assert corrupted["published"].tolist() == df["published"].tolist()

    _assert_original_not_mutated(df, snapshot)

    print("PASS: zero-fraction test on real dataset")


def _test_missing_required_columns() -> None:
    df = pd.DataFrame(
        {
            "paper_id": ["paper-001"],
            "title": ["Title"],
        }
    )

    try:
        corrupt_clean_dataframe(
            df,
            "data/results/real_corruption_log_invalid.json",
        )
    except ValueError as error:
        assert "Missing required columns" in str(error)
        print("PASS: missing required columns test")
        return

    raise AssertionError("Expected ValueError for missing required columns.")


def _test_empty_dataframe() -> None:
    df = pd.DataFrame(
        columns=[
            "paper_id",
            "title",
            "summary",
            "published",
        ]
    )

    try:
        corrupt_clean_dataframe(
            df,
            "data/results/real_corruption_log_empty.json",
        )
    except ValueError as error:
        assert "empty dataframe" in str(error)
        print("PASS: empty dataframe test")
        return

    raise AssertionError("Expected ValueError for empty dataframe.")


def _run_real_data_tests() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("Running corruption.py tests on real dataset from data/...")

    _test_corruption_basic()
    _test_reproducibility()
    _test_zero_fraction_no_change_except_rebuild()
    _test_missing_required_columns()
    _test_empty_dataframe()

    print("\nAll real data corruption tests passed successfully.")

    real_df = _load_real_clean_dataframe()
    real_corrupted = corrupt_clean_dataframe(
        real_df,
        "data/results/real_corruption_log_demo.json",
        run_date="2026-08-06T00:00:00Z",
        seed=42,
    )

    print("\nOriginal real data rows:", len(real_df))
    print("Corrupted real data rows:", len(real_corrupted))
    print("\nCorrupted sample from real dataset:")
    sample = real_corrupted[
        [
            "paper_id",
            "title",
            "summary_chars",
            "age_days",
        ]
    ].head(8)
    print(sample.to_string())


if __name__ == "__main__":
    _run_real_data_tests()