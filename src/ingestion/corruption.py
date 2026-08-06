from __future__ import annotations

import pandas as pd


from typing import Any
from pathlib import Path
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    if df.empty:
        write_json(Path(output_log_path), {"scenarios": [], "corrupted_rows": 0})
        return df.copy()

    c_df = df.copy()
    log_entries: list[dict[str, Any]] = []

    # Scenario 1: Drop latest records (e.g., first 2 records since sorted by published desc)
    if len(c_df) > 4:
        dropped_ids = c_df.iloc[:2]["paper_id"].tolist()
        c_df = c_df.iloc[2:].reset_index(drop=True)
        log_entries.append(
            {
                "scenario": "drop_latest_records",
                "count": len(dropped_ids),
                "target_paper_ids": dropped_ids,
            }
        )

    # Scenario 2: Blank summary on some rows
    if len(c_df) >= 2:
        blank_indices = [0, 1]
        blank_ids = c_df.iloc[blank_indices]["paper_id"].tolist()
        for idx in blank_indices:
            c_df.at[idx, "summary"] = ""
            c_df.at[idx, "summary_chars"] = 0
        log_entries.append(
            {
                "scenario": "blank_summary",
                "count": len(blank_ids),
                "target_paper_ids": blank_ids,
            }
        )

    # Scenario 3: Inject noise into summary
    if len(c_df) >= 4:
        noise_indices = [2, 3]
        noise_ids = c_df.iloc[noise_indices]["paper_id"].tolist()
        for idx in noise_indices:
            c_df.at[idx, "summary"] = "CORRUPTED_TEXT_GARBAGE_XYZ " * 5
            c_df.at[idx, "summary_chars"] = len(c_df.at[idx, "summary"])
        log_entries.append(
            {
                "scenario": "inject_noise",
                "count": len(noise_ids),
                "target_paper_ids": noise_ids,
            }
        )

    # Scenario 4: Truncate title
    if len(c_df) >= 3:
        trunc_indices = [1, 2]
        trunc_ids = c_df.iloc[trunc_indices]["paper_id"].tolist()
        for idx in trunc_indices:
            orig_title = c_df.at[idx, "title"]
            c_df.at[idx, "title"] = orig_title[:5] if len(orig_title) > 5 else "T"
        log_entries.append(
            {
                "scenario": "truncate_title",
                "count": len(trunc_ids),
                "target_paper_ids": trunc_ids,
            }
        )

    # Scenario 5: Stale publication date
    if len(c_df) >= 2:
        stale_indices = [0, 2]
        stale_ids = c_df.iloc[stale_indices]["paper_id"].tolist()
        for idx in stale_indices:
            c_df.at[idx, "published"] = "2020-01-01"
            c_df.at[idx, "age_days"] = 1500
        log_entries.append(
            {
                "scenario": "stale_publication_date",
                "count": len(stale_ids),
                "target_paper_ids": stale_ids,
            }
        )

    # Scenario 6: Add duplicate rows
    if len(c_df) >= 2:
        dup_rows = c_df.iloc[:2].copy()
        c_df = pd.concat([c_df, dup_rows], ignore_index=True)
        log_entries.append(
            {
                "scenario": "duplicate_rows",
                "count": len(dup_rows),
                "target_paper_ids": dup_rows["paper_id"].tolist(),
            }
        )

    # Rebuild text_for_embedding for all rows
    rebuilt_texts = []
    for _, row in c_df.iterrows():
        text = (
            f"Title: {row['title']}\n"
            f"Summary: {row['summary']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Published: {row['published']}"
        )
        rebuilt_texts.append(text)
    c_df["text_for_embedding"] = rebuilt_texts

    log_payload = {
        "scenarios": log_entries,
        "corrupted_total_rows": len(c_df),
    }
    write_json(Path(output_log_path), log_payload)

    return c_df

