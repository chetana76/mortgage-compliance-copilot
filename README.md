🏠 Mortgage Servicing & Compliance Co-Pilot

A Retrieval-Augmented Generation (RAG) assistant that answers a homeowner's
plain-language questions about their mortgage-servicing rights — grounded in
public federal (CFPB) rules, with page-level citations and a
refusal-and-escalate path to a HUD-approved housing counselor.


⚠️ Disclaimer: This tool provides general information from federal
mortgage servicing rules — not legal advice. Questions that need legal
advice, state-specific law, or personal account details are routed to a free
HUD-approved housing counselor (hud.gov).



Built for the Mastering Agentic AI bootcamp (Week 2). The corpus is
deliberately public (the CFPB Mortgage Servicing Small Entity Compliance
Guide), so the project is fully shareable with no proprietary data.


What it does

A borrower who has fallen behind on payments can ask, in their own words —
"Can they foreclose while my loss-mitigation application is pending?" — and get
a grounded, cited answer drawn straight from the rules. Anything that crosses
into legal advice or a borrower's specific account is declined and handed off to
a human counselor.

The hard part of a compliance tool isn't answering — it's knowing when not
to. This build treats that boundary as a first-class feature.


Architecture

#mermaid-r4j1-r2{font-family:"Anthropic Sans",system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:16px;fill:#191919;}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#mermaid-r4j1-r2 .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#mermaid-r4j1-r2 .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#mermaid-r4j1-r2 .error-icon{fill:#CC785C;}#mermaid-r4j1-r2 .error-text{fill:#3387a3;stroke:#3387a3;}#mermaid-r4j1-r2 .edge-thickness-normal{stroke-width:1px;}#mermaid-r4j1-r2 .edge-thickness-thick{stroke-width:3.5px;}#mermaid-r4j1-r2 .edge-pattern-solid{stroke-dasharray:0;}#mermaid-r4j1-r2 .edge-thickness-invisible{stroke-width:0;fill:none;}#mermaid-r4j1-r2 .edge-pattern-dashed{stroke-dasharray:3;}#mermaid-r4j1-r2 .edge-pattern-dotted{stroke-dasharray:2;}#mermaid-r4j1-r2 .marker{fill:#91918D;stroke:#91918D;}#mermaid-r4j1-r2 .marker.cross{stroke:#91918D;}#mermaid-r4j1-r2 svg{font-family:"Anthropic Sans",system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:16px;}#mermaid-r4j1-r2 p{margin:0;}#mermaid-r4j1-r2 .label{font-family:"Anthropic Sans",system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#191919;}#mermaid-r4j1-r2 .cluster-label text{fill:#3387a3;}#mermaid-r4j1-r2 .cluster-label span{color:#3387a3;}#mermaid-r4j1-r2 .cluster-label span p{background-color:transparent;}#mermaid-r4j1-r2 .label text,#mermaid-r4j1-r2 span{fill:#191919;color:#191919;}#mermaid-r4j1-r2 .node rect,#mermaid-r4j1-r2 .node circle,#mermaid-r4j1-r2 .node ellipse,#mermaid-r4j1-r2 .node polygon,#mermaid-r4j1-r2 .node path{fill:#F0F0EB;stroke:#D9D8D5;stroke-width:1px;}#mermaid-r4j1-r2 .rough-node .label text,#mermaid-r4j1-r2 .node .label text,#mermaid-r4j1-r2 .image-shape .label,#mermaid-r4j1-r2 .icon-shape .label{text-anchor:middle;}#mermaid-r4j1-r2 .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#mermaid-r4j1-r2 .rough-node .label,#mermaid-r4j1-r2 .node .label,#mermaid-r4j1-r2 .image-shape .label,#mermaid-r4j1-r2 .icon-shape .label{text-align:center;}#mermaid-r4j1-r2 .node.clickable{cursor:pointer;}#mermaid-r4j1-r2 .root .anchor path{fill:#91918D!important;stroke-width:0;stroke:#91918D;}#mermaid-r4j1-r2 .arrowheadPath{fill:#0b0b0b;}#mermaid-r4j1-r2 .edgePath .path{stroke:#91918D;stroke-width:1px;}#mermaid-r4j1-r2 .flowchart-link{stroke:#91918D;fill:none;}#mermaid-r4j1-r2 .edgeLabel{background-color:#F5E6D8;text-align:center;}#mermaid-r4j1-r2 .edgeLabel p{background-color:#F5E6D8;}#mermaid-r4j1-r2 .edgeLabel rect{opacity:0.5;background-color:#F5E6D8;fill:#F5E6D8;}#mermaid-r4j1-r2 .labelBkg{background-color:rgba(245, 230, 216, 0.5);}#mermaid-r4j1-r2 .cluster rect{fill:#CC785C;stroke:hsl(15, 12.3364485981%, 48.0392156863%);stroke-width:1px;}#mermaid-r4j1-r2 .cluster text{fill:#3387a3;}#mermaid-r4j1-r2 .cluster span{color:#3387a3;}#mermaid-r4j1-r2 div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:"Anthropic Sans",system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:12px;background:#CC785C;border:1px solid hsl(15, 12.3364485981%, 48.0392156863%);border-radius:2px;pointer-events:none;z-index:100;}#mermaid-r4j1-r2 .flowchartTitleText{text-anchor:middle;font-size:18px;fill:#191919;}#mermaid-r4j1-r2 rect.text{fill:none;stroke-width:0;}#mermaid-r4j1-r2 .icon-shape,#mermaid-r4j1-r2 .image-shape{background-color:#F5E6D8;text-align:center;}#mermaid-r4j1-r2 .icon-shape p,#mermaid-r4j1-r2 .image-shape p{background-color:#F5E6D8;padding:2px;}#mermaid-r4j1-r2 .icon-shape .label rect,#mermaid-r4j1-r2 .image-shape .label rect{opacity:0.5;background-color:#F5E6D8;fill:#F5E6D8;}#mermaid-r4j1-r2 .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#mermaid-r4j1-r2 .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#mermaid-r4j1-r2 .node .neo-node{stroke:#D9D8D5;}#mermaid-r4j1-r2 [data-look="neo"].node rect,#mermaid-r4j1-r2 [data-look="neo"].cluster rect,#mermaid-r4j1-r2 [data-look="neo"].node polygon{stroke:url(#mermaid-r4j1-r2-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#mermaid-r4j1-r2 [data-look="neo"].node path{stroke:url(#mermaid-r4j1-r2-gradient);stroke-width:1px;}#mermaid-r4j1-r2 [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#mermaid-r4j1-r2 [data-look="neo"].node .neo-line path{stroke:#D9D8D5;filter:none;}#mermaid-r4j1-r2 [data-look="neo"].node circle{stroke:url(#mermaid-r4j1-r2-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#mermaid-r4j1-r2 [data-look="neo"].node circle .state-start{fill:#000000;}#mermaid-r4j1-r2 [data-look="neo"].icon-shape .icon{fill:url(#mermaid-r4j1-r2-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#mermaid-r4j1-r2 [data-look="neo"].icon-shape .icon-neo path{stroke:url(#mermaid-r4j1-r2-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#mermaid-r4j1-r2 :root{--mermaid-font-family:"Anthropic Sans",system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}yesno / out-of-scopeBorrower questionRetrievedense + sparseRRF fusionLLM reranktop-4Usablecontext?Grounded,cited answerRefuse + escalateto HUD counselor

Ingestion (one-time)


Table-aware parsing — per page, detect and validate real tables, render
them to Markdown, and subtract their bounding boxes from the prose so nothing
is duplicated.
Cleaning + reconciliation — NFKC normalization and a tightly-scoped
footer filter; a source-vs-target word-count check confirms only boilerplate
was removed (100% → 97% coverage).
Chunking experiment — fixed-size vs. semantic chunking, with tables kept
atomic (one table = one chunk).
Embed + index — Qwen3-Embedding-8B via Nebius into a persistent Chroma
collection (dense) plus a BM25 index (sparse). Embeddings are cached, so
re-runs are free.


Query (per request)


Embed the question via Nebius.
Retrieve in parallel: Chroma (dense, top-20) + BM25 (sparse, top-20).
Fuse with Reciprocal Rank Fusion.
Rerank the fused top-20 → top-4 with an LLM listwise reranker (Nebius has
no cross-encoder rerank endpoint).
LangGraph spine: answer only from the retrieved chunks with page
citations — or refuse and escalate.



Key features


Hybrid retrieval — dense embeddings catch paraphrase; BM25 catches exact
section numbers (§1024.41), day counts, and dollar thresholds.
Table-aware ingestion — regulatory tables (timelines, fee conditions) stay
intact instead of being split mid-row.
LLM-as-reranker — a listwise reranker on Nebius, hardened against
reasoning-model output, with a graceful fall back to fusion order.
Refusal-and-escalate spine — discriminates by question type: a
legal-advice question is declined even when relevant chunks are retrieved.
Page-level citations — every claim is tied to a source page, e.g.
(CFPB Servicing Guide, p.174).



Tech stack

ComponentToolOrchestrationLangGraphEmbeddingsQwen3-Embedding-8B via NebiusVector DB (dense)Chroma (local, persistent)Sparse indexBM25 (rank_bm25)RerankerLLM listwise rerank (Qwen3.5 via Nebius)GenerationQwen3.5 via NebiusFrontendStreamlitCorpusCFPB Mortgage Servicing rules (public)


Repository structure

.
├── app.py                 # Streamlit chat app
├── config.py              # central settings (model IDs, paths, top-k)
├── requirements.txt
├── src/
│   ├── ingest.py          # table-aware PDF -> blocks.jsonl
│   ├── chunk.py           # fixed vs semantic chunking
│   ├── embed_index.py     # Chroma (dense) + BM25 (sparse) indexes
│   ├── retrieve.py        # hybrid retrieval + RRF + LLM rerank
│   └── answer.py          # LangGraph answer + refusal spine
└── data/
    └── raw/               # source PDF + SOURCES.md


Setup & running

bash# 1. environment (Python 3.12)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. add your Nebius key
cp .env.example .env        # then edit .env and set NEBIUS_API_KEY

# 3. build the knowledge base (one-time)
python src/ingest.py
python src/chunk.py                 # fixed
python src/chunk.py --semantic      # semantic
python src/embed_index.py --strategy fixed
python src/embed_index.py --strategy semantic

# 4a. ask from the command line
python src/answer.py --strategy semantic \
  --query "Can they foreclose while my loss mitigation application is pending?"

# 4b. or launch the chat app
streamlit run app.py


Example

Answerable question →


Q: Can they foreclose while my loss-mitigation application is pending?

A grounded answer citing §1024.41 protections with page references
(CFPB Servicing Guide, p.172 / p.174).



Out-of-scope question →


Q: Should I file for bankruptcy to stop my foreclosure?

Declined and escalated to a HUD-approved housing counselor — legal advice is
outside the tool's scope, even though relevant chunks were retrieved.




Evaluation


Status: planned. A gold set of ~12–15 borrower questions (answerable,
ambiguous, and unanswerable/out-of-scope) will measure retrieval recall,
faithfulness, answer relevance, and refusal accuracy, comparing the fixed vs.
semantic indexes. Numbers will be added when the eval is run.




Known limitations & roadmap


Two-column / sidebar pages can interleave on a minority of pages; column
detection is future work.
Single-source corpus today (the CFPB guide); roadmap adds Regulation X
(eCFR), Fannie/Freddie servicing guides, and HUD handbooks.
Reasoning-model cost/latency — a non-reasoning generation model would be
cheaper and faster.
Graph + vector retrieval for multi-hop across cross-referenced sections is
a future extension.



Cost

Built within a $1 Nebius trial credit. Embeddings are cached (paid once);
Chroma, BM25, and Streamlit are free/local. Full ingest + demo runs in the
range of $0.20–0.50.


This is a learning project. It is not affiliated with the CFPB or HUD and does
not provide legal advice.
