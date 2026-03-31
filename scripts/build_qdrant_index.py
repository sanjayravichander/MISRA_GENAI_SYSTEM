#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import uuid


# ── Paths ──────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent

DEFAULT_EXCEL_KB = PROJECT_ROOT / "data" / "knowledge" / "excel_kb" / "misra_excel_kb.corrected.json"
DEFAULT_JSON_KB = (
    PROJECT_ROOT / "data" / "knowledge" / "output_processed_01" / "misra_kb_output" / "misra_kb_chunks.jsonl"
)
DEFAULT_OUT = PROJECT_ROOT / "data" / "knowledge" / "qdrant_index"

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
COLLECTION_NAME = "misra_excel_kb"
VECTOR_DIM = 768
BATCH_SIZE = 32


# ── Chunk builders ─────────────────────────────────────────────────────────
def chunks_from_excel(records: list[dict]) -> list[dict]:
    """
    Build indexable chunks from Excel records.
    """
    chunks = []

    for rec in records:
        rid = str(rec.get("rule_id", "")).strip()
        rule_type = str(rec.get("rule_type", "")).strip()
        rule_statement = str(rec.get("rule_statement", "")).strip()
        description = str(rec.get("description", "")).strip()
        violated_code = str(rec.get("violated_code", "")).strip()

        if not rid or not rule_statement:
            continue

        core_text = f"{rid} ({rule_type}): {rule_statement}. {description}".strip()
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "rule_id": rid,
            "rule_type": rule_type,
            "chunk_type": "rule_core",
            "trust": "high",
            "source": "excel",
            "text": core_text,
            "embed_text": core_text,
            "rule_statement": rule_statement,
            "description": description,
        })

        if violated_code:
            viol_text = (
                f"{rid} violation example. "
                f"Rule: {rule_statement}. "
                f"Violated code:\n{violated_code}"
            )

            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "rule_id": rid,
                "rule_type": rule_type,
                "chunk_type": "violated_example",
                "trust": "high",
                "source": "excel",
                "text": violated_code,
                "embed_text": viol_text,
                "rule_statement": rule_statement,
            })

    return chunks


def chunks_from_json_kb(jsonl_path: Path) -> list[dict]:
    """
    Build indexable chunks from the JSONL PDF-derived KB.
    """
    if not jsonl_path.exists():
        print(f"  [SKIP] JSON KB not found at {jsonl_path} — skipping PDF-derived chunks")
        return []

    include_sections = {"rationale", "amplification", "exception", "body_text"}
    min_text_len = 40

    chunks = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            section = str(obj.get("section", "")).strip()
            if section not in include_sections:
                continue

            text = str(obj.get("text", "")).strip()
            if len(text) < min_text_len:
                continue

            rule_id = str(obj.get("guideline_id", "")).strip()
            title = str(obj.get("title", "")).strip()

            embed_text = f"{rule_id} {section} {title}: {text}".strip()

            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "rule_id": rule_id,
                "chunk_type": section,
                "trust": "medium",
                "source": "pdf_kb",
                "text": text,
                "embed_text": embed_text,
                "title": title,
            })

    return chunks


# ── Embedding ──────────────────────────────────────────────────────────────
def embed_chunks(chunks: list[dict], model) -> list[list[float]]:
    texts = [c["embed_text"] for c in chunks]
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        vecs = model.encode(
            batch,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        all_embeddings.extend(vecs.tolist())
        if (i // BATCH_SIZE) % 5 == 0:
            print(f"    Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)}", end="\r")

    print(f"    Embedded {len(texts)}/{len(texts)} chunks        ")
    return all_embeddings


# ── Qdrant builder ─────────────────────────────────────────────────────────
def build_qdrant_collection(
    chunks: list[dict],
    embeddings: list[list[float]],
    out_dir: Path,
) -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType

    out_dir.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(out_dir))

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}'")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )
    print(f"  Created collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}, cosine)")

    for field in ("rule_id", "chunk_type", "trust", "source"):
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )

    points = []
    for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        payload = {k: v for k, v in chunk.items() if k != "embed_text"}
        points.append(PointStruct(id=i, vector=vec, payload=payload))

    upload_batch = 256
    for start in range(0, len(points), upload_batch):
        batch = points[start:start + upload_batch]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        print(f"  Uploaded {min(start + upload_batch, len(points))}/{len(points)} points", end="\r")

    print(f"  Uploaded {len(points)}/{len(points)} points          ")
    info = client.get_collection(COLLECTION_NAME)
    print(f"  Collection ready: {info.points_count} vectors")


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Qdrant index (BGE embeddings) from corrected Excel KB + JSON KB"
    )
    parser.add_argument("--excel-kb", type=Path, default=DEFAULT_EXCEL_KB)
    parser.add_argument("--json-kb", type=Path, default=DEFAULT_JSON_KB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    args = parser.parse_args()

    print(f"Loading Excel KB from {args.excel_kb} ...")
    if not args.excel_kb.exists():
        print(f"  ERROR: {args.excel_kb} not found.")
        return 1

    excel_data = json.loads(args.excel_kb.read_text(encoding="utf-8"))
    excel_records = excel_data["rules"] if isinstance(excel_data, dict) and "rules" in excel_data else excel_data
    print(f"  {len(excel_records)} rules loaded from Excel KB")

    print("Building chunks ...")
    excel_chunks = chunks_from_excel(excel_records)
    print(
        f"  Excel chunks: {len(excel_chunks)} "
        f"({sum(1 for c in excel_chunks if c['chunk_type'] == 'rule_core')} rule_core + "
        f"{sum(1 for c in excel_chunks if c['chunk_type'] == 'violated_example')} violated_example)"
    )

    json_chunks = chunks_from_json_kb(args.json_kb)
    print(f"  PDF KB chunks: {len(json_chunks)}")

    all_chunks = excel_chunks + json_chunks
    print(f"  Total chunks to index: {len(all_chunks)}")

    print(f"\nLoading embedding model '{args.model}' ...")
    print("  (First run downloads the model once into Hugging Face cache)")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(args.model)
    actual_dim = model.get_sentence_embedding_dimension()
    print(f"  Model loaded — embedding dim: {actual_dim}")

    if actual_dim != VECTOR_DIM:
        print(f"  WARNING: Expected dim {VECTOR_DIM}, got {actual_dim}. Update VECTOR_DIM in this script.")

    print(f"\nEmbedding {len(all_chunks)} chunks ...")
    embeddings = embed_chunks(all_chunks, model)

    print(f"\nBuilding Qdrant collection at {args.out} ...")
    build_qdrant_collection(all_chunks, embeddings, args.out)

    meta_path = args.out / "qdrant_metadata.json"
    meta = [{k: v for k, v in c.items() if k != "embed_text"} for c in all_chunks]
    meta_path.write_text(
        json.dumps({"chunk_count": len(meta), "chunks": meta}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Metadata saved: {meta_path}")

    from collections import Counter
    type_counts = Counter(c["chunk_type"] for c in all_chunks)
    trust_counts = Counter(c["trust"] for c in all_chunks)

    print(f"\n{'=' * 60}")
    print("  Qdrant index built successfully")
    print(f"  Total vectors  : {len(all_chunks)}")
    print(f"  By chunk type  : {dict(type_counts)}")
    print(f"  By trust level : {dict(trust_counts)}")
    print(f"  Model used     : {args.model}")
    print(f"  Output dir     : {args.out}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())