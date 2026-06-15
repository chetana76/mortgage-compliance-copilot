"""
Phase 6: Answer spine (LangGraph) — grounded, cited answers + a refusal path.

Kept intentionally simple. The graph is just:

    retrieve --> have context? --> generate   (cited answer)
                              \\--> refuse     (no context found)

The generate step makes ONE Nebius call. Its prompt tells the model to answer
ONLY from the retrieved context with page citations, OR — if the context does
not support an answer, or the question needs legal / state-specific / personal-
account help — to refuse and point the borrower to a HUD-approved counselor.

CLI:
    python src/answer.py --strategy semantic \\
        --query "can they foreclose while my modification is pending?"
"""

import sys
from pathlib import Path
from typing import TypedDict

sys.path.append(str(Path(__file__).parent.parent))
import config  # noqa: E402
from retrieve import retrieve, _client  # reuse Phase 5  # noqa: E402

GEN_MAX_TOKENS = 4000  # room so a reasoning model finishes its answer

ESCALATION = (
    "I'm not able to answer that one from the federal mortgage servicing rules I "
    "have. For help with your specific situation, please reach out to a "
    "HUD-approved housing counselor — it's free, and they can look at your case. "
    "You can find one at hud.gov or through HUD's housing counseling line."
)

FOOTER = (
    "\n\n— This is general information from federal mortgage servicing rules, not "
    "legal advice. For your specific situation, contact a free HUD-approved "
    "housing counselor (hud.gov)."
)


class State(TypedDict):
    query: str
    strategy: str
    chunks: list
    answer: str


def retrieve_node(state: State) -> dict:
    chunks, _ = retrieve(state["query"], state["strategy"])
    return {"chunks": chunks}


def route(state: State) -> str:
    return "generate" if state["chunks"] else "refuse"


def refuse_node(state: State) -> dict:
    return {"answer": ESCALATION}


def generate_node(state: State) -> dict:
    context = "\n\n".join(
        f"(p.{c['meta']['page']}) {c['content']}" for c in state["chunks"])
    prompt = (
        "You are a calm, plain-language assistant for mortgage borrowers.\n"
        "Answer the borrower's QUESTION using ONLY the CONTEXT below — excerpts "
        "from federal mortgage servicing rules.\n"
        "Important: the CONTEXT is written for mortgage *servicers*, so it "
        "describes the servicer's obligations. Translate those duties into what "
        "they mean for the borrower and answer helpfully. For example, if the "
        "rules say a servicer must respond to a written notice of error, explain "
        "that the borrower can dispute by sending that written notice and what "
        "the servicer must then do.\n"
        "Guidelines:\n"
        "- Cite each fact inline as (CFPB Servicing Guide, p.X) using the page "
        "numbers shown.\n"
        "- If the CONTEXT contains relevant rules, ANSWER — even when it is "
        "phrased as the servicer's duties rather than borrower steps.\n"
        "- Refuse ONLY if the question asks for legal advice, state-specific "
        "law, the person's personal account details, or the CONTEXT is truly "
        "unrelated to the question. To refuse, reply with exactly this sentence:\n"
        f"{ESCALATION}\n\n"
        f"QUESTION: {state['query']}\n\nCONTEXT:\n{context}"
    )
    resp = _client().chat.completions.create(
        model=config.GEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=GEN_MAX_TOKENS,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        text = ESCALATION
    # add the footer only to real answers, not to a refusal
    if ESCALATION.split(".")[0] not in text:
        text += FOOTER
    return {"answer": text}


def build_graph():
    from langgraph.graph import StateGraph, END
    g = StateGraph(State)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("refuse", refuse_node)
    g.set_entry_point("retrieve")
    g.add_conditional_edges("retrieve", route,
                            {"generate": "generate", "refuse": "refuse"})
    g.add_edge("generate", END)
    g.add_edge("refuse", END)
    return g.compile()


def answer(query: str, strategy: str = "semantic"):
    app = build_graph()
    out = app.invoke({"query": query, "strategy": strategy,
                      "chunks": [], "answer": ""})
    return out["answer"], out["chunks"]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", choices=["fixed", "semantic"], default="semantic")
    ap.add_argument("--query", required=True)
    args = ap.parse_args()

    ans, chunks = answer(args.query, args.strategy)
    print("\n" + "=" * 60)
    print(ans)
    print("=" * 60)
    print(f"\n(grounded on {len(chunks)} retrieved chunks)")


if __name__ == "__main__":
    main()
