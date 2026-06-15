"""
Phase 0 milestone: prove the REQUIRED Nebius model call works.

Run this once your .env has a real NEBIUS_API_KEY. If it prints an embedding
dimension (a number like 1024 or 4096), you have satisfied the handout's
"at least one model call on Nebius Token Factory" requirement and you're
unblocked for the whole rest of the project.

    python scripts/check_nebius.py
"""

import sys
from pathlib import Path

# let this script import config.py from the project root
sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI  # noqa: E402

import config  # noqa: E402


def main() -> None:
    if not config.NEBIUS_API_KEY:
        print("❌ NEBIUS_API_KEY is not set. Add it to your .env file first.")
        sys.exit(1)

    client = OpenAI(
        base_url=config.NEBIUS_BASE_URL,
        api_key=config.NEBIUS_API_KEY,
    )

    sample = "What is the 120-day rule before a foreclosure can be filed?"
    print(f"Embedding a test sentence with model: {config.EMBED_MODEL}")

    try:
        resp = client.embeddings.create(model=config.EMBED_MODEL, input=sample)
    except Exception as e:  # broad on purpose: we want the raw error to debug
        print("❌ Call failed. Most common causes:")
        print("   - wrong EMBED_MODEL id (copy the exact one from your dashboard)")
        print("   - wrong NEBIUS_BASE_URL")
        print("   - API key not activated / out of credits")
        print(f"\nRaw error:\n{e}")
        sys.exit(1)

    vector = resp.data[0].embedding
    print(f"✅ Success. Got a {len(vector)}-dimension embedding vector.")
    print(f"   First 5 numbers: {vector[:5]}")
    print("\nYou've satisfied the Nebius requirement. Phase 0 done.")


if __name__ == "__main__":
    main()
