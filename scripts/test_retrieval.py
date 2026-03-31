from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

from fastembed import TextEmbedding
from qdrant_client import QdrantClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]

QDRANT_DB_PATH = PROJECT_ROOT / "data" / "knowledge" / "qdrant_index"
COLLECTION_NAME = "misra_excel_kb"
EMBED_MODEL_NAME = "BAAI/bge-base-en-v1.5"

TEST_QUERIES: List[Tuple[str, str]] = [
    ("unsigned integer constants must use u suffix", "Rule 7.2"),
    ("lowercase l must not be used in literal suffix", "Rule 7.3"),
    ("array with external linkage size should be specified", "Rule 8.11"),
    ("header file name must not contain quotes slash star or slash slash", "Rule 20.2"),
    ("tgmath.h should not be used", "Rule 21.11"),
]


def main() -> int:
    try:
        if not QDRANT_DB_PATH.exists():
            raise FileNotFoundError(f"Qdrant DB path not found: {QDRANT_DB_PATH}")

        print(f"[INFO] Opening local Qdrant DB: {QDRANT_DB_PATH}")
        client = QdrantClient(path=str(QDRANT_DB_PATH))

        if not client.collection_exists(COLLECTION_NAME):
            raise RuntimeError(f"Collection '{COLLECTION_NAME}' does not exist.")

        print(f"[INFO] Loading embed model: {EMBED_MODEL_NAME}")
        embedder = TextEmbedding(model_name=EMBED_MODEL_NAME)

        pass_count = 0
        fail_count = 0

        for query_text, expected_rule_id in TEST_QUERIES:
            query_vector = next(embedder.embed([query_text])).tolist()

            results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=3,
            ).points

            print("\n" + "=" * 80)
            print(f"QUERY: {query_text}")
            print(f"EXPECTED TOP-1 RULE ID: {expected_rule_id}")

            if not results:
                print("[FAIL] No retrieval results returned.")
                fail_count += 1
                continue

            for rank, item in enumerate(results, start=1):
                payload = item.payload
                rule_id = payload.get("rule_id", "")
                rule_statement = payload.get("rule_statement", "")
                score = getattr(item, "score", None)

                print(f"{rank}. rule_id={rule_id} | score={score}")
                print(f"   statement={rule_statement}")

            top_rule_id = results[0].payload.get("rule_id", "")

            if top_rule_id == expected_rule_id:
                print("[PASS] Top-1 result is correct.")
                pass_count += 1
            else:
                print("[FAIL] Top-1 result is incorrect.")
                fail_count += 1

        print("\n" + "=" * 80)
        print("Retrieval Test Summary")
        print("=" * 80)
        print(f"Passed: {pass_count}")
        print(f"Failed: {fail_count}")

        if fail_count > 0:
            return 1

        print("[SUCCESS] Retrieval is working correctly for all test queries.")
        return 0

    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())