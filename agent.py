"""Conversational agent orchestrating Ollama-powered reasoning and tool use."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import ollama

from tools import get_profile_section, get_project_details, log_recruiter_lead

MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3")
MAX_LOOPS = 5
SYSTEM_PROMPT = (
    "You are Mayank Kumar Pokhriyal, an AI Engineer & Data Scientist. "
    "Speak warmly in the first person, grounded strictly in the structured data available via tools. "
    "Never fabricate details. "
    "You have access to tools: "
    "get_profile_section(section_name:str), get_project_details(project_name:str), "
    "log_recruiter_lead(recruiter_name:str, company:str, role:str, contact:str, notes:str). "
    "Whenever a user questions skills, education, experience, projects, or preferences, "
    "call the appropriate tool before responding unless already provided in the current turn. "
    "Detect recruiter intent (interest in hiring, interview, referrals). If detected, extract "
    "recruiter_name, company, role, contact, and notes. Only call log_recruiter_lead after you have "
    "those fields; otherwise, ask respectful follow-up questions to gather them. "
    "After a successful log_recruiter_lead call, thank the recruiter and confirm receipt. "
    "All outputs must be a single JSON object with keys: thought, action, action_input, final. "
    "If action is 'tool', set action_input to the arguments (JSON object) and leave final empty. "
    "If action is 'respond', action_input must be null and final must contain the conversational reply."
)


def run_agent(user_message: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Main entry point invoked by the Streamlit UI."""
    messages = _build_message_stack(chat_history)
    messages.append({"role": "user", "content": user_message})

    lead_logged = False
    lead_payload: Optional[Dict[str, Any]] = None

    for _ in range(MAX_LOOPS):
        response = _call_model(messages)
        assistant_content = response.get("message", {}).get("content", "")
        messages.append({"role": "assistant", "content": assistant_content})

        parsed = _parse_agent_action(assistant_content)
        if parsed["action"] == "tool":
            tool_name = parsed["tool_name"]
            tool_input = parsed["tool_input"] or {}
            tool_result, tool_meta = _invoke_tool(tool_name, tool_input)
            if tool_name == "log_recruiter_lead" and tool_meta.get("status") == "success":
                lead_logged = True
                lead_payload = {**tool_input, **tool_meta}
            tool_message = json.dumps({"tool": tool_name, "result": tool_result}, ensure_ascii=False)
            messages.append({"role": "tool", "content": tool_message, "name": tool_name})
            continue

        if parsed["action"] == "respond":
            clean_response = parsed.get("final") or assistant_content

            #  ABSOLUTE CLEANUP: Remove any leftover JSON-like tool formatting
            if isinstance(clean_response, str):
                if "{" in clean_response and "}" in clean_response:
                    # Keep only the last natural paragraph
                    clean_response = clean_response.split("}")[-1].strip()

            return {
                "response": clean_response,
                "lead_logged": lead_logged,
                "lead_payload": lead_payload,
}

    fallback = "I want to make sure I get that right. Could you please rephrase the question?"
    return {"response": fallback, "lead_logged": lead_logged, "lead_payload": lead_payload}


def _build_message_stack(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        if msg["role"] in {"user", "assistant"}:
            messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def _call_model(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    try:
        return ollama.chat(model=MODEL_NAME, messages=messages)
    except Exception as exc:  # noqa: BLE001 - surface detailed failure upstream
        raise RuntimeError(
            "Failed to communicate with the local Ollama model. "
            "Ensure Ollama is running and the model is pulled."
        ) from exc


def _parse_agent_action(content: str) -> Dict[str, Any]:
    json_block = _extract_json_block(content)
    if not json_block:
        return {"action": "respond", "final": content, "tool_name": None, "tool_input": None}

    try:
        payload = json.loads(json_block)
    except json.JSONDecodeError:
        return {"action": "respond", "final": content, "tool_name": None, "tool_input": None}

    action = payload.get("action", "respond")
    if action == "tool":
        return {
            "action": "tool",
            "tool_name": payload.get("tool_name"),
            "tool_input": payload.get("action_input"),
            "final": payload.get("final"),
        }
    return {
        "action": "respond",
        "tool_name": None,
        "tool_input": None,
        "final": payload.get("final", content),
    }


def _extract_json_block(text: str) -> Optional[str]:
    text = text.strip()
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        braces = 0
        for char in candidate:
            if char == "{":
                braces += 1
            elif char == "}":
                braces -= 1
            if braces < 0:
                return None
        if braces == 0:
            return candidate
    return None


def _invoke_tool(name: str, tool_input: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    tool_map = {
        "get_profile_section": _run_get_profile_section,
        "get_project_details": _run_get_project_details,
        "log_recruiter_lead": _run_log_recruiter_lead,
    }
    if name not in tool_map:
        raise ValueError(f"Unknown tool requested: {name}")
    return tool_map[name](tool_input)


def _run_get_profile_section(tool_input: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    section = tool_input.get("section_name") if isinstance(tool_input, dict) else None
    if not section:
        raise ValueError("section_name is required for get_profile_section")
    data = get_profile_section(section)
    return data, {"status": "success"}


def _run_get_project_details(tool_input: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    project = tool_input.get("project_name") if isinstance(tool_input, dict) else None
    if not project:
        raise ValueError("project_name is required for get_project_details")
    data = get_project_details(project)
    return data, {"status": "success"}


def _run_log_recruiter_lead(tool_input: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    if not isinstance(tool_input, dict):
        raise ValueError("action_input must be an object for log_recruiter_lead")
    result = log_recruiter_lead(tool_input)
    return result, result
