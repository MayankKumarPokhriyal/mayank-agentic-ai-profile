"""Utility tools for the Mayank agent.

- Loads structured profile data from profile.json
- Provides helpers to query sections and projects
- Logs recruiter leads locally into a CSV file
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# -----------------------------
# Profile loading
# -----------------------------

_PROFILE_CACHE: Optional[Dict[str, Any]] = None
_BASE_DIR = Path(__file__).resolve().parent
_PROFILE_PATH = _BASE_DIR / "profile.json"
LEADS_DIR = _BASE_DIR / "leads"
LEADS_DIR.mkdir(exist_ok=True)
LEADS_CSV_PATH = LEADS_DIR / "recruiter_leads.csv"


def _load_profile() -> Dict[str, Any]:
    """Lazy-load structured profile data from profile.json."""
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        if not _PROFILE_PATH.exists():
            raise FileNotFoundError(f"profile.json not found at {_PROFILE_PATH}")
        with _PROFILE_PATH.open("r", encoding="utf-8") as f:
            _PROFILE_CACHE = json.load(f)
    return _PROFILE_CACHE


def refresh_profile_cache() -> None:
    """Force reload of profile.json."""
    global _PROFILE_CACHE
    _PROFILE_CACHE = None
    _load_profile()


def get_profile_section(section_name: str) -> Any:
    """
    Return a specific section from the profile (skills, education, experience, etc.)
    with some alias handling so the agent can't easily break it.
    """
    if not section_name:
        return {}

    profile = _load_profile()
    key = section_name.lower().strip()

    aliases = {
        "skills": "skills",
        "skill": "skills",
        "education": "education",
        "experience": "experience",
        "projects": "projects",
        "project": "projects",
        "job_preferences": "job_preferences",
        "job": "job_preferences",
        "preferences": "job_preferences",
        "links": "links",
        "contact": "contact",
    }

    resolved = aliases.get(key, key)
    return profile.get(resolved, {})


def get_project_details(project_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a project entry by name (case-insensitive)."""
    if not project_name:
        return None

    profile = _load_profile()
    projects = profile.get("projects", [])
    name_lower = project_name.lower().strip()

    for proj in projects:
        if proj.get("name", "").lower() == name_lower:
            return proj
    return None


# -----------------------------
# Recruiter lead logging
# -----------------------------

def log_recruiter_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log a recruiter lead to a local CSV file.

    Expected keys in `lead`:
        recruiter_name, company, role, contact, notes
    """
    required = ["recruiter_name", "company", "role", "contact"]
    missing = [k for k in required if not lead.get(k)]
    if missing:
        raise ValueError(f"Missing fields for recruiter lead: {', '.join(missing)}")

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "timestamp": timestamp,
        "recruiter_name": lead.get("recruiter_name", ""),
        "company": lead.get("company", ""),
        "role": lead.get("role", ""),
        "contact": lead.get("contact", ""),
        "notes": lead.get("notes", ""),
    }

    file_exists = LEADS_CSV_PATH.exists()
    with LEADS_CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "recruiter_name", "company", "role", "contact", "notes"],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return {
        "status": "saved_locally",
        "path": str(LEADS_CSV_PATH),
        "timestamp": timestamp,
    }