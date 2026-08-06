from __future__ import annotations


from pathlib import Path
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== [CORRUPTION FLOW] Starting Corruption -> Evaluate -> Repair -> Compare Pipeline ===")
    settings = load_settings()

    # Step 1: Load Baseline Clean Data & Metrics
    if not settings.paths.clean_csv.exists() or not settings.paths.baseline_metrics.exists():
        raise RuntimeError("Baseline clean data or metrics missing. Please run Phase 1 baseline pipeline first.")

    print("[1/7] Loading Baseline clean dataset & baseline metrics...")
    df_baseline = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # Step 2: Corrupt Data
    print("[2/7] Injecting data corruption scenarios...")
    df_corrupted = corrupt_clean_dataframe(df_baseline, settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    print(f"      Saved corrupted dataset ({len(df_corrupted)} rows) to CSV/JSON.")

    # Step 3: Rebuild Vector Index for Corrupted Data
    print("[3/7] Rebuilding vector index on Corrupted dataset...")
    corrupted_index = LocalEmbeddingIndex.build(
        df_corrupted,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    # Step 4: Evaluate Corrupted Pipeline
    print("[4/7] Evaluating Corrupted pipeline on baseline test set...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, report_name="corrupted_quality")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, report_path=settings.paths.quality_dir / "corrupted_freshness.json"
    )

    # Step 5: Repair Data from Raw Source Snapshot
    print("[5/7] Repairing dataset from raw source snapshot...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date=now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    print(f"      Saved repaired dataset ({len(df_repaired)} rows) to CSV/JSON.")

    # Step 6: Rebuild Vector Index for Repaired Data & Evaluate
    print("[6/7] Rebuilding vector index & evaluating Repaired pipeline...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(df_repaired, settings, report_name="repaired_quality")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, report_path=settings.paths.quality_dir / "repaired_freshness.json"
    )

    # Step 7: Comparison Report Generation
    print("[7/7] Generating Comparison Markdown Report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("\n=== [CORRUPTION FLOW SUMMARY] ===")
    print(
        f"Baseline  - Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0)*100:.2f}%, Token F1: {baseline_metrics.get('mean_token_f1', 0):.4f}, Judge Score: {baseline_metrics.get('mean_judge_score', 0):.2f}"
    )
    print(
        f"Corrupted - Hit Rate: {corrupted_bundle.summary.get('retrieval_hit_rate', 0)*100:.2f}%, Token F1: {corrupted_bundle.summary.get('mean_token_f1', 0):.4f}, Judge Score: {corrupted_bundle.summary.get('mean_judge_score', 0):.2f}"
    )
    print(
        f"Repaired  - Hit Rate: {repaired_bundle.summary.get('retrieval_hit_rate', 0)*100:.2f}%, Token F1: {repaired_bundle.summary.get('mean_token_f1', 0):.4f}, Judge Score: {repaired_bundle.summary.get('mean_judge_score', 0):.2f}"
    )
    print(f"=== [CORRUPTION FLOW COMPLETE] Comparison report saved to '{settings.paths.comparison_report}' ===")


if __name__ == "__main__":
    main()

