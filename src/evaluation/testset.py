from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < 4:
        raise ValueError(f"Need at least 4 papers to build a test set, got {len(df)}.")

    # Pick up to 6 representative papers spread across the dataset
    n_papers = min(6, len(df))
    step = max(1, len(df) // n_papers)
    sample = df.iloc[::step].head(n_papers).reset_index(drop=True)

    items: list[dict[str, Any]] = []
    idx = 0

    for _, row in sample.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        doc_ids = [paper_id]

        # summary question
        if row.get("summary", "").strip():
            items.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "summary",
                    "question": f"What is the paper '{title}' about?",
                    "ground_truth": row["summary"].strip(),
                    "ground_truth_doc_ids": doc_ids,
                }
            )
            idx += 1

        # authors question
        if row.get("authors_joined", "").strip():
            items.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "authors",
                    "question": f"Who authored the paper '{title}'?",
                    "ground_truth": row["authors_joined"].strip(),
                    "ground_truth_doc_ids": doc_ids,
                }
            )
            idx += 1

        # date question
        if row.get("published", "").strip():
            items.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "date",
                    "question": f"When was the paper '{title}' published?",
                    "ground_truth": row["published"].strip(),
                    "ground_truth_doc_ids": doc_ids,
                }
            )
            idx += 1

        # categories question
        if row.get("categories_joined", "").strip():
            items.append(
                {
                    "id": f"q{idx:03d}",
                    "question_type": "categories",
                    "question": f"What categories does the paper '{title}' belong to?",
                    "ground_truth": row["categories_joined"].strip(),
                    "ground_truth_doc_ids": doc_ids,
                }
            )
            idx += 1

    write_json(output_path, items)
    return items
