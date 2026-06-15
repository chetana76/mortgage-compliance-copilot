"""
Phase 4: Embed + index — build the hybrid (dense + sparse) knowledge base.

Reads data/processed/chunks_{strategy}.jsonl and builds two indexes:
    indexes/{strategy}/chroma/      persistent Chroma vector index   (DENSE)
    indexes/{strategy}/bm25.pkl     BM25 index over the same chunks  (SPARSE)

Together these are the two halves of the hybrid retriever (reranking is Phase 5).
Dense vectors come from Nebius and are cached on disk, so you embed once — every
re-run after that is free.

Run one strategy at a time (cheap, deliberate, cached):
    python src/embed_index.py --strategy fixed
    python src/embed_index.py --strategy semantic
"""

import argparse
import hashlib
import json
import pickle
import re
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config  # noqa: E402

INDEX_ROOT = config.ROOT / "indexes"
EMBED_CACHE = config.ROOT / ".embed_cache_chunks.pkl"
BATCH = 128  # chunks embedded per Nebius call


# ------------------------------------------------------------------ load
def load_chunks(strategy: str) -> list[dict]:
    path = config.DATA_PROCESSED / f"chunks_{strategy}.jsonl"
    if not path.exists():
        print(f"❌ {path} not found. Run src/chunk.py "
              f"{'--semantic' if strategy == 'semantic' else ''}first.")
        sys.exit(1)
    chunks = [json.loads(line) for line in path.open()]
    # guard: drop any empty-content chunks so we never index junk
    good = [c for c in chunks if c.get("content", "").strip()]
    if len(good) != len(chunks):
        print(f"  note: skipped {len(chunks) - len(good)} empty chunk(s)")
    return good


# ------------------------------------------------------------------ dense
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed chunk texts in BATCHES via Nebius, cached on disk by content hash.
    Returns vectors aligned 1:1 with `texts`."""
    from openai import OpenAI

    cache: dict = {}
    if EMBED_CACHE.exists():
        try:
            cache = pickle.loads(EMBED_CACHE.read_bytes())
        except Exception:
            cache = {}

    def key(s: str) -> str:
        return hashlib.sha256((config.EMBED_MODEL + "\x00" + s).encode()).hexdigest()

    uniq = list(dict.fromkeys(texts))
    todo = [s for s in uniq if key(s) not in cache]
    print(f"  {len(uniq)} unique chunks | {len(uniq) - len(todo)} cached | "
          f"{len(todo)} to embed")

    if todo:
        client = OpenAI(base_url=config.NEBIUS_BASE_URL, api_key=config.NEBIUS_API_KEY)
        done = 0
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            for attempt in range(3):
                try:
                    resp = client.embeddings.create(
                        model=config.EMBED_MODEL, input=batch)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    print(f"  ...transient error, retrying: {e}")
                    time.sleep(2 * (attempt + 1))
            for s, d in zip(batch, resp.data):
                cache[key(s)] = d.embedding
            done += len(batch)
            print(f"  embedded {done}/{len(todo)} ...", flush=True)
        EMBED_CACHE.write_bytes(pickle.dumps(cache))
        print(f"  embedding cache saved -> {EMBED_CACHE.name}")

    return [cache[key(s)] for s in texts]


def build_chroma(strategy: str, chunks: list[dict],
                 vectors: list[list[float]]) -> Path:
    import chromadb

    chroma_dir = INDEX_ROOT / strategy / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    name = f"mortgage_{strategy}"
    col = client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"})

    # upsert keyed by chunk_id -> safe to re-run without duplicating
    col.upsert(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=vectors,
        documents=[c["content"] for c in chunks],
        metadatas=[{"source": c["source"], "page": c["page"],
                    "type": c["type"], "strategy": c["strategy"]}
                   for c in chunks],
    )
    print(f"  Chroma collection '{name}': {col.count()} vectors -> {chroma_dir}")
    return chroma_dir


# ------------------------------------------------------------------ sparse
def tokenize(text: str) -> list[str]:
    """Lowercase tokens, keeping dotted runs like '1024.41' intact so exact
    citation/section queries can match in BM25."""
    return re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)*", text.lower())


def build_bm25(strategy: str, chunks: list[dict]) -> Path:
    from rank_bm25 import BM25Okapi

    tokenized = [tokenize(c["content"]) for c in chunks]
    bm25 = BM25Okapi(tokenized)

    out_dir = INDEX_ROOT / strategy
    out_dir.mkdir(parents=True, exist_ok=True)
    bm25_path = out_dir / "bm25.pkl"
    with bm25_path.open("wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)
    print(f"  BM25 index: {len(chunks)} chunks -> {bm25_path}")

    # free sanity check (no embeddings needed): does a term retrieve sensibly?
    probe = "loss mitigation"
    scores = bm25.get_scores(tokenize(probe))
    top = max(range(len(scores)), key=lambda i: scores[i])
    print(f"  BM25 self-test '{probe}' -> top hit {chunks[top]['chunk_id']} "
          f"(p{chunks[top]['page']}): {chunks[top]['content'][:60]}...")
    return bm25_path


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["fixed", "semantic"], required=True,
                    help="which chunk set to index")
    args = ap.parse_args()

    chunks = load_chunks(args.strategy)
    print(f"Indexing {len(chunks)} '{args.strategy}' chunks...")

    print("Dense (Nebius embeddings -> Chroma):")
    vectors = embed_texts([c["content"] for c in chunks])
    build_chroma(args.strategy, chunks, vectors)

    print("Sparse (BM25):")
    build_bm25(args.strategy, chunks)

    print(f"\n✅ Hybrid index ready for '{args.strategy}'. "
          f"Run the other strategy too, then on to Phase 5 (retrieve + rerank).")


if __name__ == "__main__":
    main()
