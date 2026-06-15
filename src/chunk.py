"""
Phase 3: Chunking experiment — fixed-size vs semantic.

Reads data/processed/blocks.jsonl and produces chunk sets:
    data/processed/chunks_fixed.jsonl      (free, no API calls)
    data/processed/chunks_semantic.jsonl   (uses Nebius embeddings -> costs $)

Rules:
  - PROSE blocks are split by the chosen strategy.
  - TABLE blocks are kept ATOMIC — one table = one chunk, never split.
  - Every chunk carries source + page so you can cite it later.

Run the free baseline first:
    python src/chunk.py                 # fixed-size only
Then add the metered run when ready:
    python src/chunk.py --semantic      # builds the semantic set
If both sets exist, a side-by-side comparison prints automatically.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config  # noqa: E402

from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

BLOCKS = config.DATA_PROCESSED / "blocks.jsonl"


def load_blocks() -> list[dict]:
    if not BLOCKS.exists():
        print(f"❌ {BLOCKS} not found. Run src/ingest.py first.")
        sys.exit(1)
    with BLOCKS.open() as f:
        return [json.loads(line) for line in f]


def tables_as_chunks(table_blocks: list[dict], strategy: str) -> list[dict]:
    """Each table stays whole — one chunk per table block."""
    return [
        {"source": b["source"], "page": b["page"], "type": "table",
         "strategy": strategy, "content": b["content"]}
        for b in table_blocks
    ]


def prose_chunks_fixed(prose_blocks: list[dict]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.FIXED_CHUNK_SIZE,
        chunk_overlap=config.FIXED_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],  # prefer natural boundaries
    )
    chunks = []
    for b in prose_blocks:
        for piece in splitter.split_text(b["content"]):
            chunks.append({"source": b["source"], "page": b["page"],
                           "type": "prose", "strategy": "fixed", "content": piece})
    return chunks


def prose_chunks_semantic(prose_blocks: list[dict]) -> list[dict]:
    # Imported here so the free path runs without langchain-experimental installed.
    from langchain_experimental.text_splitter import SemanticChunker
    from langchain_openai import OpenAIEmbeddings
    from langchain.embeddings import CacheBackedEmbeddings
    from langchain.storage import LocalFileStore

    base = OpenAIEmbeddings(
        model=config.EMBED_MODEL,
        base_url=config.NEBIUS_BASE_URL,
        api_key=config.NEBIUS_API_KEY,
        check_embedding_ctx_length=False,  # Nebius isn't OpenAI's tokenizer
    )
    # Cache embeddings to disk so re-running the experiment costs $0 the 2nd time.
    store = LocalFileStore(str(config.ROOT / ".embed_cache"))
    embeddings = CacheBackedEmbeddings.from_bytes_store(
        base, store, namespace=config.EMBED_MODEL.replace("/", "_")
    )

    chunker = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
    chunks = []
    for b in prose_blocks:
        for piece in chunker.split_text(b["content"]):
            chunks.append({"source": b["source"], "page": b["page"],
                           "type": "prose", "strategy": "semantic", "content": piece})
    return chunks


def build(strategy: str, blocks: list[dict]) -> Path:
    prose = [b for b in blocks if b["type"] == "prose"]
    tables = [b for b in blocks if b["type"] == "table"]

    if strategy == "fixed":
        prose_chunks = prose_chunks_fixed(prose)
    else:
        print("Embedding sentences for semantic boundaries (first Nebius spend; "
              "cached so re-runs are free)...")
        prose_chunks = prose_chunks_semantic(prose)

    all_chunks = prose_chunks + tables_as_chunks(tables, strategy)
    for i, c in enumerate(all_chunks):
        c["chunk_id"] = f"{strategy}-{i:04d}"

    out = config.DATA_PROCESSED / f"chunks_{strategy}.jsonl"
    with out.open("w") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")
    return out


def stats_for(path: Path) -> dict:
    chunks = [json.loads(l) for l in path.open()]
    sizes = [len(c["content"]) for c in chunks if c["type"] == "prose"]
    return {
        "total": len(chunks),
        "prose": sum(1 for c in chunks if c["type"] == "prose"),
        "table": sum(1 for c in chunks if c["type"] == "table"),
        "min": min(sizes) if sizes else 0,
        "avg": int(statistics.mean(sizes)) if sizes else 0,
        "median": int(statistics.median(sizes)) if sizes else 0,
        "max": max(sizes) if sizes else 0,
    }


def print_report(strategy: str, path: Path) -> None:
    s = stats_for(path)
    print("\n" + "=" * 52)
    print(f"CHUNKING REPORT — {strategy.upper()}")
    print("=" * 52)
    print(f"  Total chunks: {s['total']}  (prose {s['prose']}, table {s['table']})")
    print(f"  Prose chunk size (chars): min {s['min']} | avg {s['avg']} | "
          f"median {s['median']} | max {s['max']}")
    print(f"  Written to: {path}")


def print_comparison() -> None:
    fp = config.DATA_PROCESSED / "chunks_fixed.jsonl"
    sp = config.DATA_PROCESSED / "chunks_semantic.jsonl"
    if not (fp.exists() and sp.exists()):
        return
    f, s = stats_for(fp), stats_for(sp)
    print("\n" + "=" * 52)
    print("SIDE-BY-SIDE: fixed vs semantic")
    print("=" * 52)
    print(f"  {'metric':<22}{'fixed':>12}{'semantic':>14}")
    for label, key in [("total chunks", "total"), ("prose chunks", "prose"),
                       ("avg prose chars", "avg"), ("median prose chars", "median"),
                       ("max prose chars", "max")]:
        print(f"  {label:<22}{f[key]:>12}{s[key]:>14}")
    print("\n  Read it like an experiment: fewer, more even chunks usually means")
    print("  cleaner boundaries. Real proof comes in Phase 8 (retrieval quality).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--semantic", action="store_true",
                    help="build the semantic set (uses Nebius embeddings)")
    args = ap.parse_args()

    blocks = load_blocks()
    strategy = "semantic" if args.semantic else "fixed"
    out = build(strategy, blocks)
    print_report(strategy, out)
    print_comparison()


if __name__ == "__main__":
    main()
