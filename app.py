"""Streamlit interface for the Mayank agentic professional profile."""
from __future__ import annotations

import streamlit as st

from agent import run_agent

st.set_page_config(page_title="Mayank | Agentic AI Profile", page_icon="🧠", layout="wide")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "leads" not in st.session_state:
    st.session_state["leads"] = []

st.title("Mayank Kumar Pokhriyal — Agentic AI Resume")
st.caption("Chat with my AI twin to learn about my experience, skills, and availability.")

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask me about my background, projects, or availability…")

if prompt:
    user_turn = {"role": "user", "content": prompt}
    st.session_state["messages"].append(user_turn)
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        agent_result = run_agent(prompt, st.session_state["messages"][:-1])
        assistant_turn = {
            "role": "assistant",
            "content": agent_result["response"],
        }
        st.session_state["messages"].append(assistant_turn)
        with st.chat_message("assistant"):
            st.markdown(agent_result["response"])

        if agent_result.get("lead_logged"):
            st.session_state["leads"].append(agent_result.get("lead_payload", {}))
            st.sidebar.success("Recruiter lead captured securely.")
    except Exception as exc:  # noqa: BLE001 - show a friendly message to the user
        error_message = (
            "I ran into an issue responding just now. Please ensure the backend services are running "
            "(Ollama and Google Sheets credentials) and try again."
        )
        st.error(error_message)
        st.session_state["messages"].pop()  # remove user turn if we failed to reply
        st.session_state.setdefault("errors", []).append(str(exc))

with st.sidebar.expander("Latest Recruiter Lead", expanded=False):
    if st.session_state["leads"]:
        lead = st.session_state["leads"][-1]
        st.json(lead)
    else:
        st.write("No recruiter leads captured yet.")
