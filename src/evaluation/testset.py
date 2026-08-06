from __future__ import annotations

from typing import Any

import pandas as pd


from typing import Any
from pathlib import Path
import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    if df.empty:
        test_set = []
        write_json(Path(output_path), test_set)
        return test_set

    # Pick top N papers across the dataframe
    sample_df = df.head(8)
    test_set: list[dict[str, Any]] = []
    q_counter = 1

    for _, row in sample_df.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors_joined = str(row["authors_joined"])
        published = str(row["published"])
        categories_joined = str(row["categories_joined"])

        # Summary question
        test_set.append(
            {
                "id": f"q_{q_counter}",
                "question_type": "summary",
                "question": f"What is the main topic or summary of the paper titled '{title}'?",
                "ground_truth": summary,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_counter += 1

        # Authors question
        test_set.append(
            {
                "id": f"q_{q_counter}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper titled '{title}'?",
                "ground_truth": authors_joined,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_counter += 1

        # Date question
        test_set.append(
            {
                "id": f"q_{q_counter}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": published,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_counter += 1

        # Categories question
        test_set.append(
            {
                "id": f"q_{q_counter}",
                "question_type": "categories",
                "question": f"What subjects or categories does the paper '{title}' belong to?",
                "ground_truth": categories_joined,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        q_counter += 1

    write_json(Path(output_path), test_set)
    return test_set

