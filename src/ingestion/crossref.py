from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
import html
from pathlib import Path
import random
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5
REQUEST_TIMEOUT_SECONDS = 30


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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _clean_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        # Crossref normally exposes abstracts as JATS/XML.  Some deposits use
        # `description` instead, so keep it as the documented fallback.
        summary = _clean_text(item.get("abstract")) or _clean_text(item.get("description"))
        if not paper_id or not title or not summary or paper_id in seen_ids:
            continue

        authors = _parse_authors(item.get("author"))
        categories = _text_list(item.get("subject"))
        links = item.get("link") if isinstance(item.get("link"), list) else []

        abs_url = _clean_text(item.get("URL"))
        if not abs_url:
            resource = item.get("resource")
            if isinstance(resource, dict):
                primary = resource.get("primary")
                if isinstance(primary, dict):
                    abs_url = _clean_text(primary.get("URL"))

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=_crossref_date(
                    item.get("published-print")
                    or item.get("published-online")
                    or item.get("published")
                    or item.get("issued")
                    or item.get("created")
                ),
                updated=_crossref_date(item.get("indexed") or item.get("deposited")),
                abs_url=abs_url,
                pdf_url=_pdf_url(links),
                comment=_first_text(item.get("container-title")),
            )
        )
        seen_ids.add(paper_id)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params: dict[str, str | int] = {
        "query": settings.source_query,
        "rows": settings.max_results,
    }
    if settings.source_filter.strip():
        params["filter"] = settings.source_filter

    headers = {
        "Accept": "application/json",
        "User-Agent": "data-observability-lab/0.1 (Crossref ingestion)",
    }
    response: requests.Response | None = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(_backoff_seconds(attempt, None))
            continue

        if response.status_code not in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
            break
        if attempt == MAX_ATTEMPTS - 1:
            response.raise_for_status()
        time.sleep(_backoff_seconds(attempt, response.headers.get("Retry-After")))
    else:  # Defensive: the loop always returns, breaks, or raises.
        raise RuntimeError("Crossref request failed without a response.")

    assert response is not None
    # Preserve the exact successful response body before parsing/transforming it.
    # This also leaves an audit artifact if Crossref ever returns malformed JSON.
    ensure_parent(settings.paths.raw_api_response)
    settings.paths.raw_api_response.write_bytes(response.content)

    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Crossref returned a JSON value that is not an object.")

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records snapshot must contain a JSON list: {path}")

    records: list[PaperRecord] = []
    field_names = set(PaperRecord.__dataclass_fields__)
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Record at index {index} is not a JSON object.")
        missing = field_names.difference(item)
        if missing:
            missing_names = ", ".join(sorted(missing))
            raise ValueError(f"Record at index {index} is missing fields: {missing_names}")
        values = {name: item[name] for name in field_names}
        values["authors"] = list(values["authors"] or [])
        values["categories"] = list(values["categories"] or [])
        records.append(PaperRecord(**values))
    return records


def _clean_text(value: Any) -> str:
    """Convert Crossref scalar text/JATS fragments to normalized plain text."""
    if not isinstance(value, str):
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return normalize_whitespace(html.unescape(without_tags))


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return next((_clean_text(item) for item in value if _clean_text(item)), "")
    return _clean_text(value)


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _parse_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("name"))
        if not name:
            name = normalize_whitespace(
                " ".join(
                    part
                    for part in (
                        _clean_text(author.get("given")),
                        _clean_text(author.get("family")),
                    )
                    if part
                )
            )
        if name:
            authors.append(name)
    return authors


def _crossref_date(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    date_time = _clean_text(value.get("date-time"))
    if date_time:
        return date_time

    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
        return ""
    parts = date_parts[0]
    if not parts:
        return ""
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return datetime(year, month, day).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _pdf_url(links: list[Any]) -> str:
    for link in links:
        if not isinstance(link, dict):
            continue
        content_type = _clean_text(link.get("content-type")).lower()
        url = _clean_text(link.get("URL"))
        if url and (content_type == "application/pdf" or url.lower().endswith(".pdf")):
            return url
    return ""


def _backoff_seconds(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                now = datetime.now(retry_at.tzinfo)
                return max(0.0, (retry_at - now).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    # Exponential backoff (1, 2, 4, ...) plus small jitter to avoid a retry herd.
    return (2**attempt) + random.uniform(0.0, 0.25)
