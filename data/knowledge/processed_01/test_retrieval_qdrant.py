#!/usr/bin/env python3
"""
test_retrieval_qdrant.py

Cheap retrieval-only evaluation for the MISRA Qdrant index.
Runs against all rules without calling the expensive LLM.

Evaluation logic
----------------
For each rule in misra_excel_kb.json, use one or more cheap queries:
- rule_statement
- description
- combined query

Then check:
- top-1 match rate
- top-3 hit rate
- top-5 hit rate

Usage
-----
python test_retrieval_qdrant.py
python test_retrieval_qdrant.py --top-k 5
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parents[3]
DEFAULT_KB = PROJECT_ROOT / "data" / "knowledge" / "excel_kb" / "misra_excel_kb.json"
DEFAULT_INDEX = PROJECT_ROOT / "data" / "knowledge" / "qdrant_index"
DEFAULT_COLLECTION = "misra_rules"
DEFAULT_MODEL = "BAAI/bge-base-en-v1.5"

def load_rules(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["rules"]

def build_queries(rule: dict) -> list[tuple[str, str]]:
    rid = rule["rule_id"]
    stmt = (rule.get("rule_statement") or "").strip()
    desc = (rule.get("description") or "").strip()

    queries = []
    if stmt:
        queries.append(("statement", stmt))
    if desc:
        queries.append(("description", desc))
    combined = f"{rid}. {stmt}. {desc}".strip()
    if combined:
        queries.append(("combined", combined))
    return queries

def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Qdrant retrieval accuracy")
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not args.kb.exists():
        print(f"[ERROR] KB not found: {args.kb}")
        return 1
    if not args.index_dir.exists():
        print(f"[ERROR] Qdrant index dir not found: {args.index_dir}")
        print("Build the Qdrant index first.")
        return 1

    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient

    print(f"Loading KB: {args.kb}")
    rules = load_rules(args.kb)
    print(f"Loaded {len(rules)} rules")

    print(f"Loading model: {args.model}")
    model = SentenceTransformer(args.model)

    print(f"Opening Qdrant index: {args.index_dir}")
    client = QdrantClient(path=str(args.index_dir))

    top1 = 0
    top3 = 0
    top5 = 0
    failures = []
    query_type_stats = Counter()

    for i, rule in enumerate(rules, start=1):
        rid = rule["rule_id"]
        queries = build_queries(rule)

        best_rank = None
        best_query_type = None
        best_results = []

        for qtype, query_text in queries:
            query_vec = model.encode(
                query_text,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            ).tolist()

            hits = client.search(
                collection_name=args.collection,
                query_vector=query_vec,
                limit=max(args.top_k, 5),
            )

            ranked_rule_ids = [h.payload.get("rule_id", "") for h in hits]
            if rid in ranked_rule_ids:
                rank = ranked_rule_ids.index(rid) + 1
                if best_rank is None or rank < best_rank:
                    best_rank = rank
                    best_query_type = qtype
                    best_results = ranked_rule_ids

        if best_rank == 1:
            top1 += 1
        if best_rank is not None and best_rank <= 3:
            top3 += 1
        if best_rank is not None and best_rank <= 5:
            top5 += 1

        if best_rank is None or best_rank > 3:
            failures.append({
                "rule_id": rid,
                "best_rank": best_rank,
                "best_query_type": best_query_type,
                "statement": rule.get("rule_statement", ""),
                "description": rule.get("description", ""),
                "top_results": best_results,
            })
        if best_query_type:
            query_type_stats[best_query_type] += 1

        if i % 10 == 0 or i == len(rules):
            print(f"Checked {i}/{len(rules)} rules", end="\r")

    print(f"Checked {len(rules)}/{len(rules)} rules")

    total = len(rules)
    print("\n" + "=" * 72)
    print("Retrieval Evaluation Summary")
    print("=" * 72)
    print(f"Rules tested  : {total}")
    print(f"Top-1 accuracy: {top1}/{total} = {top1/total:.1%}")
    print(f"Top-3 hit rate: {top3}/{total} = {top3/total:.1%}")
    print(f"Top-5 hit rate: {top5}/{total} = {top5/total:.1%}")
    print(f"Best query    : {dict(query_type_stats)}")

    if failures:
        print(f"\nFailures / weak matches (rank > 3 or not found): {len(failures)}")
        for item in failures[:25]:
            print(
                f"  - {item['rule_id']}: best_rank={item['best_rank']}, "
                f"query_type={item['best_query_type']}, top_results={item['top_results']}"
            )

        out_path = args.index_dir / "retrieval_eval_failures.json"
        out_path.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved detailed failures to: {out_path}")
    else:
        print("\nAll rules retrieved within top-3.")

    client.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
