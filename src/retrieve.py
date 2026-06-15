"""
Phase 5: Hybrid retrieval + LLM rerank.

For a query and a chunk strategy (fixed|semantic):
  1. DENSE  — embed the query via Nebius, search Chroma   (top RETRIEVE_TOP_K)
  2. SPARSE — BM25 over the same chunks                   (top RETRIEVE_TOP_K)
  3. FUSE   — Reciprocal Rank Fusion of the two lists
  4. RERANK — a Nebius chat model scores the fused top-K and keeps RERANK_TOP_N

Nebius has no cross-encoder rerank endpoint, so step 4 uses an LLM as a
*listwise* reranker. The parser is hardened against reasoning models: it tolerates
an empty/None reply and extracts the final JSON array even when the model wraps
it in reasoning text. If nothing parseable comes back, we fall back to the fusion
order — so retrieval never hard-fails on a rerank hiccup.

CLI (manual test):
    python src/retrieve.py --strategy semantic \\
        --query "can they foreclose while my modification is pending?"
"""

import argparse
import json
import pickle
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config  # noqa: E402

INDEX_ROOT = config.ROOT / "indexes"
RRF_K = 60            # RRF damping constant (standard default)
RERANK_TRUNC = 500    # chars of each candidate shown to the reranker
RERANK_MAX_TOKENS = 1024  # room for reasoning models to finish + emit the array


# --------------------------------------------------- Nebius calls (isolated)
def _client():
    from openai import OpenAI
    return OpenAI(base_url=config.NEBIUS_BASE_URL, api_key=config.NEBIUS_API_KEY)


def _embed_query(text: str) -> list[float]:
    resp = _client().embeddings.create(model=config.EMBED_MODEL, input=[text])
    return resp.data[0].embedding


def _llm_rerank_call(prompt: str) -> str:
    resp = _client().chat.completions.create(
        model=config.GEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=RERANK_MAX_TOKENS,
    )
    msg = resp.choices[0].message
    # reasoning models may leave .content empty and put text in .reasoning_content
    return msg.content or getattr(msg, "reasoning_content", "") or ""


# --------------------------------------------------- the two retrievers
def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)*", text.lower())


def dense_search(query: str, strategy: str, k: int) -> list[dict]:
    import chromadb
    client = chromadb.PersistentClient(path=str(INDEX_ROOT / strategy / "chroma"))
    col = client.get_collection(f"mortgage_{strategy}")
    res = col.query(query_embeddings=[_embed_query(query)], n_results=k)
    out = []
    for cid, doc, meta in zip(res["ids"][0], res["documents"][0],
                              res["metadatas"][0]):
        out.append({"chunk_id": cid, "content": doc, "meta": meta})
    return out


def sparse_search(query: str, strategy: str, k: int) -> list[dict]:
    with (INDEX_ROOT / strategy / "bm25.pkl").open("rb") as f:
        d = pickle.load(f)
    bm25, chunks = d["bm25"], d["chunks"]
    scores = bm25.get_scores(_tokenize(query))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    out = []
    for i in order:
        c = chunks[i]
        out.append({"chunk_id": c["chunk_id"], "content": c["content"],
                    "meta": {"source": c["source"], "page": c["page"],
                             "type": c["type"], "strategy": c["strategy"]}})
    return out


# --------------------------------------------------- fuse + rerank
def rrf_fuse(dense: list[dict], sparse: list[dict], k: int = RRF_K) -> list[dict]:
    """Reciprocal Rank Fusion: blends two ranked lists by rank, not by score,
    so Chroma's cosine scale and BM25's scale never need reconciling."""
    scores: dict = {}
    store: dict = {}
    for lst in (dense, sparse):
        for rank, item in enumerate(lst):
            cid = item["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            store[cid] = item
    ordered = sorted(scores, key=lambda c: scores[c], reverse=True)
    return [store[c] for c in ordered]


def _parse_idxs(raw: str, n: int) -> list[int]:
    """Pull passage indices out of the model's reply. Tolerates None, code
    fences, and reasoning text wrapped around the answer by scanning for the
    LAST valid JSON array of numbers."""
    if not raw:
        return []
    cleaned = raw.replace("```json", "").replace("```", "")
    # every bracketed group; prefer the last one (a reasoning model's final answer)
    for arr_text in reversed(re.findall(r"\[[^\[\]]*\]", cleaned)):
        try:
            arr = json.loads(arr_text)
        except Exception:
            continue
        idxs = []
        for x in arr:
            try:
                i = int(x)
            except (TypeError, ValueError):
                continue
            if 0 <= i < n:
                idxs.append(i)
        if idxs:
            return idxs
    return []


def llm_rerank(query: str, candidates: list[dict], top_n: int) -> list[dict]:
    if len(candidates) <= top_n:
        return candidates
    lines = [f"[{i}] {c['content'][:RERANK_TRUNC]}" for i, c in enumerate(candidates)]
    prompt = (
        "You are a retrieval reranker for a mortgage servicing compliance "
        "assistant.\n"
        f"From the PASSAGES below, choose the {top_n} most relevant to answering "
        "the QUESTION, ordered most relevant first.\n"
        "Respond with ONLY a JSON array of passage numbers as the final line, "
        "e.g. [3,0,5,1].\n\n"
        f"QUESTION: {query}\n\nPASSAGES:\n" + "\n".join(lines)
    )
    idxs = _parse_idxs(_llm_rerank_call(prompt), len(candidates))
    if not idxs:
        return candidates[:top_n]  # graceful fallback to fusion order

    picked = [candidates[i] for i in idxs[:top_n]]
    if len(picked) < top_n:  # model returned too few — pad from fusion order
        for c in candidates:
            if c not in picked:
                picked.append(c)
            if len(picked) == top_n:
                break
    return picked


def retrieve(query: str, strategy: str, top_k: int = None,
             top_n: int = None) -> tuple[list[dict], dict]:
    top_k = top_k or config.RETRIEVE_TOP_K
    top_n = top_n or config.RERANK_TOP_N
    dense = dense_search(query, strategy, top_k)
    sparse = sparse_search(query, strategy, top_k)
    fused = rrf_fuse(dense, sparse)[:top_k]
    final = llm_rerank(query, fused, top_n)
    return final, {"dense": len(dense), "sparse": len(sparse), "fused": len(fused)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["fixed", "semantic"], required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--top-n", type=int, default=None)
    args = ap.parse_args()

    final, stats = retrieve(args.query, args.strategy, top_n=args.top_n)
    print(f"\nQuery: {args.query}")
    print(f"dense {stats['dense']} + sparse {stats['sparse']} "
          f"-> fused {stats['fused']} -> rerank {len(final)}\n")
    for i, c in enumerate(final, 1):
        m = c["meta"]
        print(f"{i}. {c['chunk_id']} [{m['type']} p{m['page']}]")
        print(f"   {c['content'][:160].strip()}...\n")


if __name__ == "__main__":
    main()
