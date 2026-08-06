from __future__ import annotations


import sys
from pathlib import Path

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== [PHASE 1] Starting Baseline Data Pipeline ===")
    settings = load_settings()

    # Step 1: Raw Ingestion
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("[1/6] Fetching raw records from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print("[1/6] Loading existing raw records from JSON snapshot...")
        records = load_raw_records(settings.paths.raw_records_json)

    print(f"      Fetched/Loaded {len(records)} raw paper records.")

    # Step 2: Data Cleaning & Transformation
    print("[2/6] Cleaning raw records & constructing DataFrame...")
    df = build_clean_dataframe(records, run_date=now_utc())
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"      Saved cleaned dataset ({len(df)} rows) to CSV/JSON.")

    # Step 3: Vector Indexing
    print("[3/6] Building ChromaDB vector index...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"      Indexed {len(index.documents)} documents into Chroma collection '{index.collection_name}'.")

    # Step 4: Evaluation Test Set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("[4/6] Generating benchmark test set...")
        build_test_set(df, settings.paths.eval_testset)
    else:
        print("[4/6] Using existing benchmark test set...")

    # Step 5: Baseline Pipeline Evaluation
    print("[5/6] Evaluating RAG pipeline against test set...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print("      Baseline Evaluation Metrics:")
    print(f"        - Samples: {bundle.summary.get('samples')}")
    print(f"        - Retrieval Hit Rate: {bundle.summary.get('retrieval_hit_rate') * 100:.2f}%")
    print(f"        - Mean Token F1: {bundle.summary.get('mean_token_f1'):.4f}")
    print(f"        - Judge Accuracy: {bundle.summary.get('judge_accuracy') * 100:.2f}%")
    print(f"        - Mean Judge Score: {bundle.summary.get('mean_judge_score'):.2f} / 5.0")

    # Step 6: Data Observability & Reporting
    print("[6/6] Running data quality checks & generating Phase 1 report...")
    quality_res = run_data_quality_checks(df, settings, report_name="baseline_quality")
    freshness_res = build_freshness_report(df, settings, settings.paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "fetched_records": len(records),
        "cleaned_records": len(df),
    }

    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_res,
        freshness=freshness_res,
    )

    print(f"=== [PHASE 1 COMPLETE] Report saved to '{settings.paths.baseline_report}' ===")


if __name__ == "__main__":
    main()

