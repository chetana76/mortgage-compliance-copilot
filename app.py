"""
Streamlit chat app for the Mortgage Servicing & Compliance Co-Pilot.

Run from the project root:
    streamlit run app.py

It wraps src/answer.py: type a borrower question, get a grounded, cited answer
(or a refusal + HUD-counselor escalation), with the retrieved sources shown.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
from answer import answer  # noqa: E402

st.set_page_config(
    page_title="Mortgage Servicing Compliance Co-Pilot",
    page_icon="🏠",
    layout="centered",
)

st.title("🏠 Mortgage Servicing Compliance Co-Pilot")
st.caption(
    "Plain-language answers about your mortgage servicing rights, grounded in "
    "public federal (CFPB) servicing rules — every answer cites its source."
)
st.warning(
    "This tool gives **general information** from federal mortgage servicing "
    "rules — **not legal advice**. For help with your specific situation, "
    "contact a free **HUD-approved housing counselor** (hud.gov).",
    icon="⚠️",
)

SAMPLE_QUESTIONS = [
    "Can they foreclose while my loss mitigation application is pending?",
    "How do I dispute an error on my mortgage statement?",
    "When does my servicer have to contact me after I miss a payment?",
    "Should I file for bankruptcy to stop my foreclosure?",  # refusal demo
]

with st.sidebar:
    st.header("Settings")
    strategy = st.radio(
        "Retrieval index (chunking strategy)",
        ["semantic", "fixed"],
        index=0,
        help="Two indexes were built as an experiment. Semantic keeps coherent "
             "passages whole; fixed splits at a character budget.",
    )
    st.divider()
    st.subheader("Try asking")
    for q in SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True):
            st.session_state["pending"] = q
    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# render history
for m in st.session_state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander(f"Sources ({len(m['sources'])} passages retrieved)"):
                for c in m["sources"]:
                    meta = c.get("meta", {})
                    st.markdown(
                        f"**p.{meta.get('page', '?')}** · `{c.get('chunk_id', '')}` "
                        f"· {meta.get('type', '')}"
                    )
                    st.caption(c.get("content", "")[:400] + "…")


def handle(query: str) -> None:
    st.session_state["messages"].append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Searching the rules and checking the citations…"):
            try:
                ans, chunks = answer(query, strategy)
            except Exception as e:  # keep the UI alive on a backend hiccup
                ans, chunks = (
                    "Something went wrong reaching the model or index. "
                    f"Please try again.\n\n`{type(e).__name__}: {e}`",
                    [],
                )
        st.markdown(ans)
        if chunks:
            with st.expander(f"Sources ({len(chunks)} passages retrieved)"):
                for c in chunks:
                    meta = c.get("meta", {})
                    st.markdown(
                        f"**p.{meta.get('page', '?')}** · `{c.get('chunk_id', '')}` "
                        f"· {meta.get('type', '')}"
                    )
                    st.caption(c.get("content", "")[:400] + "…")
    st.session_state["messages"].append(
        {"role": "assistant", "content": ans, "sources": chunks}
    )


# a sample-button click queues a question
pending = st.session_state.pop("pending", None)
typed = st.chat_input("Ask about your mortgage servicing rights…")

if pending:
    handle(pending)
elif typed:
    handle(typed)
