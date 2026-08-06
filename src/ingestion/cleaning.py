from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _parse_date(value: str) -> str | None:
    """Accept YYYY-MM-DD, YYYY-MM, or YYYY and normalise to YYYY-MM-DD."""
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    run_date_naive = run_date.replace(tzinfo=None)

    rows = []
    for rec in records:
        title = normalize_whitespace(_strip_html(rec.title or ""))
        summary = normalize_whitespace(_strip_html(rec.summary or ""))
        if not title or not rec.paper_id:
            continue

        published = _parse_date(rec.published) if rec.published else None
        updated = _parse_date(rec.updated) if rec.updated else published

        if published:
            try:
                pub_dt = datetime.strptime(published, "%Y-%m-%d")
                age_days = (run_date_naive - pub_dt).days
            except ValueError:
                age_days = None
        else:
            age_days = None

        authors = [normalize_whitespace(a) for a in (rec.authors or []) if a and a.strip()]
        categories = [normalize_whitespace(c) for c in (rec.categories or []) if c and c.strip()]
        primary_category = normalize_whitespace(rec.primary_category or "")
        if not primary_category and categories:
            primary_category = categories[0]

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Abstract: {summary}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}"
        ).strip()

        rows.append(
            {
                "paper_id": rec.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published or "",
                "updated": updated or "",
                "abs_url": rec.abs_url or "",
                "pdf_url": rec.pdf_url or "",
                "comment": rec.comment or "",
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["paper_id"])
    df = df[df["title"].str.strip().ne("")]
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    return df
