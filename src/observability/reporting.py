from __future__ import annotations

from typing import Any

from core.utils import write_text


def _cell(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    separator = ["---" for _ in headers]
    rendered = [headers, separator, *rows]
    return "\n".join(f"| {' | '.join(_cell(cell) for cell in row)} |" for row in rendered)


def _quality_rows(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return (payload or {}).get("checks", {})


def _check_summary(check: dict[str, Any] | None) -> str:
    if not check:
        return "N/A"
    detail = ", ".join(f"{key}={value}" for key, value in check.items() if key != "passed")
    return f"{'PASS' if check.get('passed') else 'FAIL'} ({detail})"


def _delta(after: Any, before: Any) -> str:
    if isinstance(after, (int, float)) and not isinstance(after, bool) and isinstance(before, (int, float)) and not isinstance(before, bool):
        return f"{after - before:+.4f}"
    return "N/A"

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a baseline report only from supplied, auditable artifacts."""
    metric_names = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    quality_rows = [[name, _check_summary(check)] for name, check in _quality_rows(quality).items()]
    sections = [
        "# Phase 1 Baseline Report",
        "## Source and dataset",
        _table(["Field", "Value"], [[key, value] for key, value in source_summary.items()]),
        "## Evaluation metrics",
        _table(["Metric", "Value"], [[name, metrics.get(name)] for name in metric_names]),
        "## Data quality",
        f"Overall status: **{_cell(quality.get('passed'))}**\n\n" + _table(["Check", "Result"], quality_rows),
        "## Freshness",
        _table(["Field", "Value"], [[key, value] for key, value in freshness.items()]),
        "## Evidence",
        "Metrics, quality and freshness values above are generated from the saved pipeline artifacts.",
    ]
    write_text(report_path, "\n\n".join(sections) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Compare baseline, corrupted and repaired states without claiming unsupported recovery."""
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    metric_rows = [
        [
            name,
            baseline_metrics.get(name),
            corrupted_metrics.get(name),
            repaired_metrics.get(name),
            _delta(corrupted_metrics.get(name), baseline_metrics.get(name)),
            _delta(repaired_metrics.get(name), corrupted_metrics.get(name)),
        ]
        for name in metric_names
    ]
    check_names = sorted(set(_quality_rows(baseline_quality)) | set(_quality_rows(corrupted_quality)) | set(_quality_rows(repaired_quality)))
    quality_rows = [
        [
            name,
            _check_summary(_quality_rows(baseline_quality).get(name)),
            _check_summary(_quality_rows(corrupted_quality).get(name)),
            _check_summary(_quality_rows(repaired_quality).get(name)),
        ]
        for name in check_names
    ]
    freshness_rows = [
        [key, (baseline_freshness or {}).get(key), corrupted_freshness.get(key), repaired_freshness.get(key)]
        for key in ["latest_published", "oldest_published", "stale_rows", "total_rows", "is_fresh"]
    ]
    sections = [
        "# Corruption and Repair Comparison Report",
        "## Evaluation metrics",
        _table(
            ["Metric", "Baseline", "Corrupted", "Repaired", "Corrupted - baseline", "Repaired - corrupted"],
            metric_rows,
        ),
        "## Data quality",
        _table(["Check", "Baseline", "Corrupted", "Repaired"], quality_rows),
        "## Freshness",
        _table(["Signal", "Baseline", "Corrupted", "Repaired"], freshness_rows),
        "## Interpretation",
        "Use the deltas and quality signals above to support conclusions; do not claim recovery unless repaired artifacts show it.",
    ]
    write_text(report_path, "\n\n".join(sections) + "\n")
