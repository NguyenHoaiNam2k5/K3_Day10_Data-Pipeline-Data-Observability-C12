from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


from dataclasses import asdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw_abstract: str) -> str:
    if not raw_abstract:
        return ""
    # Strip JATS XML / HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", raw_abstract)
    return normalize_whitespace(cleaned)


def _format_date(date_obj: dict | None) -> str:
    if not date_obj or "date-parts" not in date_obj or not date_obj["date-parts"]:
        return "2024-01-01"
    parts = date_obj["date-parts"][0]
    if len(parts) >= 3:
        return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
    if len(parts) == 2:
        return f"{parts[0]:04d}-{parts[1]:02d}-01"
    if len(parts) == 1:
        return f"{parts[0]:04d}-01-01"
    return "2024-01-01"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # Extract title
        titles = item.get("title", [])
        title = normalize_whitespace(titles[0]) if titles else ""
        if not title:
            continue

        # Extract abstract/summary
        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)
        if not summary:
            # Fallback to title or container-title if abstract is missing
            container = item.get("container-title", [])
            container_str = container[0] if container else ""
            summary = f"Abstract unavailable. Paper published in {container_str}." if container_str else title

        # Extract DOI / paper_id
        doi = item.get("DOI", "").strip()
        paper_id = safe_slug(doi) if doi else safe_slug(title[:40])

        # Extract authors
        author_list = item.get("author", [])
        authors = []
        for auth in author_list:
            given = auth.get("given", "").strip()
            family = auth.get("family", "").strip()
            name = f"{given} {family}".strip() or family or given
            if name:
                authors.append(name)
        if not authors:
            authors = ["Unknown Author"]

        # Extract categories / subjects
        subjects = item.get("subject", [])
        categories = [normalize_whitespace(s) for s in subjects if s]
        if not categories:
            categories = ["Computer Science", "Artificial Intelligence"]
        primary_category = categories[0]

        # Extract publication dates
        pub_date_obj = item.get("published-print") or item.get("published-online") or item.get("issued") or item.get("created")
        published = _format_date(pub_date_obj)
        updated = _format_date(item.get("deposited") or pub_date_obj)

        # URLs
        abs_url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
        pdf_url = abs_url
        link_list = item.get("link", [])
        for link in link_list:
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", abs_url)
                break

        comment = item.get("type", "journal-article")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": "DataPipelineObservabilityLab/1.0 (mailto:student@example.com)"}

    payload = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                payload = response.json()
                break
            elif response.status_code in {429, 503, 504}:
                time.sleep(2 * (attempt + 1))
            else:
                response.raise_for_status()
        except Exception as exc:
            if attempt == max_retries - 1:
                # If network/API fails, check if we have raw_api_response snapshot saved locally
                if settings.paths.raw_api_response.exists():
                    payload = read_json(settings.paths.raw_api_response)
                    break
                raise RuntimeError(f"Failed to fetch Crossref records after {max_retries} attempts: {exc}") from exc
            time.sleep(2 * (attempt + 1))

    if payload is None:
        raise RuntimeError("Failed to fetch payload from Crossref API.")

    # Save raw API response
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)

    # Save raw records snapshot
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    data = read_json(path)
    records = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item["primary_category"],
                published=item["published"],
                updated=item["updated"],
                abs_url=item["abs_url"],
                pdf_url=item["pdf_url"],
                comment=item["comment"],
            )
        )
    return records

