"""
Central configuration for the Mortgage Servicing Compliance Co-pilot.

Keeping every setting in one file is a data-engineering habit that pays off:
when you tune chunk size or swap an embedding model, you change it HERE, not
in five scattered scripts.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # reads your .env file into environment variables

# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).parent
DATA_RAW = ROOT / "data" / "raw"          # original source PDFs go here
DATA_PROCESSED = ROOT / "data" / "processed"  # cleaned text / chunks go here
VECTOR_DIR = ROOT / "data" / "chroma"     # local vector store lives here

# --- Nebius Token Factory (the REQUIRED model call) ----------------------
# Nebius exposes an OpenAI-compatible API, so we can use the standard openai
# client and just point it at their base URL.
#
# CONFIRM both of these from your Nebius dashboard after you sign up:
#   1. the base URL (Token Factory endpoint)
#   2. the exact embedding model id (the string below is a sensible default,
#      but model ids change — copy the real one from your dashboard)
NEBIUS_BASE_URL = os.getenv(
    "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1"
)
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")  # never hard-code this

EMBED_MODEL = os.getenv("EMBED_MODEL", "Qwen/Qwen3-Embedding-8B")

# Generation model. PROTECT YOUR $1 TRIAL: develop on the cheapest small instruct
# model your dashboard offers, and only swap to a nicer model for the final demo
# + eval recording. Confirm the exact id (and its price) in your dashboard.
GEN_MODEL = "Qwen/Qwen3.5-397B-A17B-fast"

# --- Cost guardrails (your $1 trial) -------------------------------------
MAX_OUTPUT_TOKENS = 500   # hard cap so an answer can never run long and burn $
# Embed-once rule: Phase 4 will persist the vector store to VECTOR_DIR and SKIP
# re-embedding if it already exists. Re-running a debug loop should cost $0.

# --- Chunking experiment knobs (Phase 3) ---------------------------------
# These are the two strategies you'll compare head-to-head.
FIXED_CHUNK_SIZE = 800        # characters, for the fixed-size baseline
FIXED_CHUNK_OVERLAP = 120     # overlap so you don't slice a sentence in half

# --- Retrieval knobs (Phase 5) -------------------------------------------
RETRIEVE_TOP_K = 20           # pull wide...
RERANK_TOP_N = 4              # ...then rerank down to the best few
