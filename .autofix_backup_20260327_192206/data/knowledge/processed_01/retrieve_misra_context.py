                                                                                                                                                                                                                                                                                                                                                                                      #!/usr/bin/env python3
"""
retrieve_misra_context.py  —  Phase 6b: Retrieve relevant MISRA KB chunks per warning.

Usage
-----
  python retrieve_misra_context.py <parsed_warnings.json> <faiss_dir> <output.json>
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
TOP_K_EXACT      = 10
TOP_K_SEMANTIC   = 6
SECTION_PRIORITY = {
    "rationale": 0, "amplification": 1, "body_text": 2,
    "title": 3, "exception": 4, "example": 5,
}


# ---------------------------------------------------------------------------
# Index loader
# ---------------------------------------------------------------------------

def load_index(faiss_dir: Path):
    import faiss
    index_path = faiss_dir / "misra_faiss.index"
    meta_path  = faiss_dir / "misra_metadata.json"

    if not index_path.exists():
        raise FileNotFoundError(f"FAISS index not found: {index_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata not found: {meta_path}")

    index      = faiss.read_index(str(index_path))
    meta_raw   = json.loads(meta_path.read_text(encoding="utf-8"))
    chunks     = meta_raw["chunks"]

    by_rule: Dict[str, List[int]] = {}
    for c in chunks:
        gid = c.get("guideline_id", "")
        by_rule.setdefault(gid, []).append(c["chunk_index"])

    return index, chunks, by_rule


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

def build_query(warning: Dict[str, Any]) -> str:
    parts = [
        warning.get("rule_id", ""),
        warning.get("checker_name", ""),
        warning.get("message", ""),
        warning.get("function_name", ""),
    ]
    return " ".join(p for p in parts if p).strip()


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_for_warning(
    warning: Dict[str, Any],
    index,
    chunks: List[Dict],
    by_rule: Dict[str, List[int]],
    model,
) -> List[Dict[str, Any]]:
    import numpy as np

    rule_id    = warning.get("rule_id", "").strip()
    retrieved  = []
    seen       = set()

    # Strategy 1: exact rule_id match
    if rule_id and rule_id in by_rule:
        exact_sorted = sorted(
            by_rule[rule_id],
            key=lambda i: SECTION_PRIORITY.get(chunks[i].get("section", ""), 99)
        )
        for i in exact_sorted[:TOP_K_EXACT]:
            retrieved.append({**chunks[i], "retrieval_method": "exact_rule_match"})
            seen.add(i)

    # Strategy 2: semantic fallback
    query_text = build_query(warning)
    if query_text:
        q_vec = model.encode(
            [query_text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32)

        k = TOP_K_SEMANTIC + len(seen)
        scores, indices = index.search(q_vec, min(k, index.ntotal))

        added = 0
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx in seen:
                continue
            chunk      = chunks[idx]
            chunk_rule = chunk.get("guideline_id", "")
            if seen and chunk_rule == rule_id:
                continue
            retrieved.append({
                **chunk,
                "retrieval_method": "semantic",
                "semantic_score":   float(score),
            })
            seen.add(idx)
            added += 1
            if added >= TOP_K_SEMANTIC:
                break

    return retrieved


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python retrieve_misra_context.py <warnings.json> <faiss_dir> <output.json>")
        return 2

    warnings_path = Path(sys.argv[1])
    faiss_dir     = Path(sys.argv[2])
    out_path      = Path(sys.argv[3])

    # --- validate inputs before doing anything ---
    if not warnings_path.exists():
        print(f"ERROR: warnings file not found: {warnings_path}")
        return 1
    if not faiss_dir.exists():
        print(f"ERROR: faiss_dir not found: {faiss_dir}")
        print(f"  Run build_faiss_index.py first.")
        return 1

    try:
        print("Loading FAISS index ...")
        index, chunks, by_rule = load_index(faiss_dir)
        print(f"  {index.ntotal} vectors loaded")
    except Exception as e:
        print(f"ERROR loading FAISS index: {e}")
        traceback.print_exc()
        return 1

    try:
        print(f"Loading embedding model '{EMBEDDING_MODEL}' ...")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        print("  Model loaded")
    except Exception as e:
        print(f"ERROR loading embedding model: {e}")
        traceback.print_exc()
        return 1

    try:
        print(f"Loading warnings from {warnings_path} ...")
        payload  = json.loads(warnings_path.read_text(encoding="utf-8"))
        warnings = payload["warnings"]
        print(f"  {len(warnings)} warnings loaded")
    except Exception as e:
        print(f"ERROR loading warnings: {e}")
        traceback.print_exc()
        return 1

    print("Retrieving MISRA context per warning ...")
    enriched = []
    for w in warnings:
        try:
            retrieved = retrieve_for_warning(w, index, chunks, by_rule, model)
            enriched.append({**w, "misra_context": retrieved})
            exact = sum(1 for r in retrieved if r["retrieval_method"] == "exact_rule_match")
            sem   = sum(1 for r in retrieved if r["retrieval_method"] == "semantic")
            print(f"  {w['warning_id']}  {w['rule_id']:12s}  {exact} exact + {sem} semantic chunks")
        except Exception as e:
            print(f"  ERROR on {w.get('warning_id')}: {e}")
            traceback.print_exc()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"warning_count": len(enriched), "warnings": enriched},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nDone. Output: {out_path}")
    print(f"Enriched {len(enriched)} warnings with MISRA context.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())