#!/usr/bin/env python3
"""
build_faiss_index.py  —  Phase 5: Build FAISS vector index from MISRA KB chunks.

What this does
--------------
1. Loads misra_kb_chunks.jsonl (523 section-level chunks)
2. Embeds each chunk using sentence-transformers (all-MiniLM-L6-v2, runs fully offline)
3. Builds a FAISS flat L2 index (exact nearest-neighbour, no approximation)
4. Saves the index + a chunk metadata store to disk

Why FAISS flat (not IVF/HNSW)
-------------------------------
523 chunks is tiny. Flat search is exact and takes <1ms per query at this size.
No training step, no tuning, fully deterministic.

Why all-MiniLM-L6-v2
---------------------
22MB model, runs on CPU in ~5ms per sentence, good semantic quality for
technical English prose. Does NOT require a GPU or internet after first download.

Security note
-------------
All processing is local. No data leaves the machine. The .index file and
metadata.json are plain files — inspect them any time.

Usage
-----
  python build_faiss_index.py <chunks.jsonl> <output_dir>

Output
------
  <output_dir>/misra_faiss.index   — FAISS index file
  <output_dir>/misra_metadata.json — chunk metadata (everything except embeddings)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # 22MB, CPU-only, fully offline after download
BATCH_SIZE = 64                          # embed N chunks at once; safe for 16GB RAM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_chunks(path: Path) -> List[Dict[str, Any]]:
    chunks = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def build_embedding_text(chunk: Dict[str, Any]) -> str:
    """
    Build the string that gets embedded for a chunk.

    We prefix with guideline_id + section + title so that retrieval
    returns semantically relevant context even for short text chunks.
    The title anchors the embedding to the rule identity; the text
    provides the semantic content.
    """
    parts = [
        f"{chunk.get('guideline_id', '')} {chunk.get('section', '')}",
        chunk.get("title", ""),
        chunk.get("text", ""),
    ]
    return " | ".join(p.strip() for p in parts if p.strip())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python build_faiss_index.py <chunks.jsonl> <output_dir>")
        return 2

    chunks_path = Path(sys.argv[1])
    output_dir  = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load chunks
    print(f"Loading chunks from {chunks_path} ...")
    chunks = load_chunks(chunks_path)
    print(f"  Loaded {len(chunks)} chunks")

    # 2. Load embedding model
    print(f"Loading embedding model '{EMBEDDING_MODEL}' ...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    dim = model.get_sentence_embedding_dimension()
    print(f"  Embedding dimension: {dim}")

    # 3. Embed all chunks
    print("Embedding chunks ...")
    texts = [build_embedding_text(c) for c in chunks]
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # cosine similarity via dot product on normalised vecs
    )
    embeddings = embeddings.astype(np.float32)
    print(f"  Embeddings shape: {embeddings.shape}")

    # 4. Build FAISS index
    # IndexFlatIP = inner product on normalised vectors = cosine similarity
    print("Building FAISS index ...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"  Index size: {index.ntotal} vectors")

    # 5. Save index
    index_path = output_dir / "misra_faiss.index"
    faiss.write_index(index, str(index_path))
    print(f"  Index saved: {index_path}")

    # 6. Save metadata (everything except the embedding vectors)
    metadata = []
    for i, chunk in enumerate(chunks):
        metadata.append({
            "chunk_index": i,
            "guideline_id":    chunk.get("guideline_id"),
            "short_id":        chunk.get("short_id"),
            "guideline_type":  chunk.get("guideline_type"),
            "section":         chunk.get("section"),
            "title":           chunk.get("title"),
            "category":        chunk.get("category"),
            "analysis":        chunk.get("analysis", ""),
            "applies_to":      chunk.get("applies_to", []),
            "c_standard_refs": chunk.get("c_standard_refs", ""),
            "text":            chunk.get("text"),
        })

    meta_path = output_dir / "misra_metadata.json"
    meta_path.write_text(
        json.dumps({"embedding_model": EMBEDDING_MODEL, "dim": dim,
                    "chunk_count": len(metadata), "chunks": metadata},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Metadata saved: {meta_path}")
    print(f"\nDone. Index ready for retrieval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())