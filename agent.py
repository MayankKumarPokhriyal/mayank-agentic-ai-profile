"""Conversational agent orchestrating Ollama-powered reasoning and local tools."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import ollama

from tools import get_profile_section, get_project_details, log_recruiter_lead

MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3")

SYSTEM_PROMPT = (
    "You are Mayank Kumar Pokhriyal, an AI Engineer & Data Scientist.\n"
    "You speak warmly in the first person and represent my real professional profile.\n"
    "You must stay truthful and consistent with the following structured data:\n"
    "- Education, experience, skills, projects, job preferences, and links.\n"
    "If you don't know something from the profile, say so honestly.\n"
    "Do NOT output JSON, brackets, or tool instructions. Speak like a human.\n"
)


def run_agent(user_message: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Main entry point invoked by the Streamlit UI.

    - Uses Ollama to answer general questions
    - Detects recruiter intent and logs leads locally (CSV) as an autonomous task
    """
    # First: check if this looks like a recruiter message
    if _looks_like_recruiter_message(user_message):
        lead, extracted = _extract_recruiter_lead(user_message)
        lead_logged = False
        lead_payload: Optional[Dict[str, Any]] = None

        if lead and _has_minimum_lead_fields(lead):
            try:
                log_result = log_recruiter_lead(lead)
                lead_logged = True
                lead_payload = {**lead, **log_result}
                reply = (
                    "Thank you for reaching out about this opportunity.\n\n"
                    f"I've recorded your details as:\n"
                    f"- Name: {lead.get('recruiter_name')}\n"
                    f"- Company: {lead.get('company')}\n"
                    f"- Role: {lead.get('role')}\n"
                    f"- Contact: {lead.get('contact')}\n"
                    f"- Notes: {lead.get('notes', '')}\n\n"
                    "I'll review this role and get back to you as soon as possible."
                )
                return {
                    "response": reply,
                    "lead_logged": lead_logged,
                    "lead_payload": lead_payload,
                }
            except Exception:
                # If logging fails, still respond gracefully
                reply = (
                    "Thanks for your interest and for sharing your details. "
                    "I attempted to record your information but ran into an internal logging issue. "
                    "You can also share your details via email at mayankpokhriyal96@gmail.com."
                )
                return {
                    "response": reply,
                    "lead_logged": False,
                    "lead_payload": None,
                }

        # Not enough info: ask a follow-up
        reply = (
            "Thanks for reaching out about a potential opportunity!\n\n"
            "To properly record this, could you please share:\n"
            "- Your name\n"
            "- Company\n"
            "- Role you're hiring for\n"
            "- Best contact email or phone\n"
        )
        return {
            "response": reply,
            "lead_logged": False,
            "lead_payload": None,
        }

    # Normal profile / Q&A mode
    answer = _answer_with_profile(user_message, chat_history)
    return {
        "response": answer,
        "lead_logged": False,
        "lead_payload": None,
    }


def _answer_with_profile(user_message: str, history: List[Dict[str, str]]) -> str:
    """
    Use Ollama to answer, while injecting structured profile snippets
    relevant to the question (skills, education, experience, projects).
    """
    profile_snippets = _build_profile_context(user_message)

    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + profile_snippets}]
    for msg in history:
        if msg["role"] in {"user", "assistant"}:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = ollama.chat(model=MODEL_NAME, messages=messages)
        content = resp.get("message", {}).get("content", "").strip()
        if not content:
            return "I heard your question, but I'm not sure how to answer that. Could you rephrase?"
        return content
    except Exception:
        return (
            "I ran into an issue talking to my local AI engine (Ollama). "
            "Please make sure the Ollama server is running and the model is available."
        )


def _build_profile_context(user_message: str) -> str:
    """Builds a small textual context from profile.json based on the question type."""
    lower = user_message.lower()
    parts: List[str] = []

    if any(k in lower for k in ["education", "degree", "university", "college"]):
        edu = get_profile_section("education")
        if edu:
            edu_lines = [
                f"- {e.get('degree')} at {e.get('institution')} ({e.get('period')})"
                for e in edu
            ]
            parts.append("Education:\n" + "\n".join(edu_lines))

    if any(k in lower for k in ["experience", "work", "job", "roles", "kyndryl", "ibm"]):
        exp = get_profile_section("experience")
        if exp:
            exp_lines = [
                f"- {e.get('title')} at {e.get('company')} ({e.get('period')})"
                for e in exp
            ]
            parts.append("Experience:\n" + "\n".join(exp_lines))

    if any(k in lower for k in ["skill", "stack", "tech", "tools"]):
        skills = get_profile_section("skills")
        if skills:
            parts.append(
                "Skills:\n"
                f"- Languages: {', '.join(skills.get('languages', []))}\n"
                f"- ML/DL: {', '.join(skills.get('ml_dl', []))}\n"
                f"- Tools: {', '.join(skills.get('tools', []))}\n"
                f"- Domains: {', '.join(skills.get('domains', []))}"
            )

    if "project" in lower:
        projs = get_profile_section("projects")
        if projs:
            proj_lines = [f"- {p.get('name')}: {p.get('description')}" for p in projs[:5]]
            parts.append("Projects (subset):\n" + "\n".join(proj_lines))

    return "\n\n".join(parts)


# -----------------------------
# Recruiter detection & extraction
# -----------------------------

def _looks_like_recruiter_message(text: str) -> bool:
    """Heuristic to detect recruiter / hiring intent."""
    lower = text.lower()
    return any(k in lower for k in ["hiring", "recruiter", "role", "position", "job", "opening"]) and any(
        k in lower for k in ["email", "@", "contact", "reach", "phone"]
    )


def _extract_recruiter_lead(text: str) -> (Optional[Dict[str, Any]], str):
    """
    Use a small LLM prompt to extract recruiter lead fields from a free-form message.

    Returns (lead_dict, raw_response_text).
    """
    extraction_system = (
        "You are an information extraction assistant.\n"
        "Given a message from a recruiter, extract the following fields and return ONLY valid JSON:\n"
        "{\n"
        '  "recruiter_name": "...",\n'
        '  "company": "...",\n'
        '  "role": "...",\n'
        '  "contact": "...",\n'
        '  "notes": "..." \n'
        "}\n"
        "If you can't find a field, set it to an empty string. Do not include any explanation or extra text."
    )

    try:
        resp = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": extraction_system},
                {"role": "user", "content": text},
            ],
        )
        content = resp.get("message", {}).get("content", "").strip()
        lead = json.loads(content)
        return lead, content
    except Exception:
        return None, ""


def _has_minimum_lead_fields(lead: Dict[str, Any]) -> bool:
    """Check if we have enough fields to log a recruiter."""
    if not lead:
        return False
    return bool(lead.get("recruiter_name") and lead.get("company") and lead.get("role") and lead.get("contact"))