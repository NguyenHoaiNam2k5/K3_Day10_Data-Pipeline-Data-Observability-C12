from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


from dataclasses import asdict
from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "text_for_embedding",
                "age_days",
            ]
        )

    rows = []
    run_dt = run_date.replace(tzinfo=None)

    for record in records:
        rec_dict = asdict(record)
        title = normalize_whitespace(rec_dict["title"])
        summary = normalize_whitespace(rec_dict["summary"])

        if not title or len(summary) < 10:
            continue

        authors = rec_dict.get("authors", [])
        categories = rec_dict.get("categories", [])
        authors_joined = ", ".join(authors) if authors else "Unknown Author"
        categories_joined = ", ".join(categories) if categories else "General"

        pub_str = rec_dict.get("published", "2024-01-01")
        try:
            pub_dt = datetime.strptime(pub_str[:10], "%Y-%m-%d")
        except Exception:
            pub_dt = datetime(2024, 1, 1)

        age_days = max(0, (run_dt - pub_dt).days)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Summary: {summary}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {pub_str}"
        )

        rec_dict.update(
            {
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
                "age_days": age_days,
            }
        )
        rows.append(rec_dict)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Drop duplicates by paper_id or title
    df = df.drop_duplicates(subset=["paper_id"]).drop_duplicates(subset=["title"])

    # Sort by published descending
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df

