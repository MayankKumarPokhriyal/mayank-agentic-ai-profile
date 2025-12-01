"""Utility tools for the Mayank agent.

These helpers keep profile access and recruiter lead logging encapsulated.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import gspread
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_PROFILE_CACHE: Optional[Dict[str, Any]] = None
_PROFILE_PATH = Path(__file__).resolve().parent / "profile.json"
SERVICE_ACCOUNT_FILE = Path(__file__).resolve().parent / "service_account.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
SHEET_TITLE = os.getenv("GOOGLE_SHEET_TITLE", "Recruiter_Leads")
WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Recruiter_Leads")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")


def _load_profile() -> Dict[str, Any]:
    """Lazy-load the structured profile data from disk."""
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        if not _PROFILE_PATH.exists():
            raise FileNotFoundError(f"Profile file not found at {_PROFILE_PATH}")
        with _PROFILE_PATH.open("r", encoding="utf-8") as handle:
            _PROFILE_CACHE = json.load(handle)
        logger.debug("Profile data loaded into cache")
    return _PROFILE_CACHE


def refresh_profile_cache() -> None:
    """Force a reload of the profile cache."""
    global _PROFILE_CACHE
    _PROFILE_CACHE = None
    _load_profile()


def get_profile_section(section_name: str) -> Optional[Any]:
    """Return a specific section from the profile JSON using case-insensitive keys."""
    if not section_name:
        return None
    profile = _load_profile()
    normalized_key = section_name.lower().strip()
    for key, value in profile.items():
        if key.lower() == normalized_key:
            return value
    return None


def get_project_details(project_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve a project entry by name with case-insensitive matching."""
    if not project_name:
        return None
    profile = _load_profile()
    projects = profile.get("projects", [])
    for project in projects:
        if project.get("name", "").lower() == project_name.lower().strip():
            return project
    return None


def _get_gspread_client() -> gspread.Client:
    """Authenticate with Google Sheets using the local service account file."""
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(
            "Google service account credentials are missing. "
            f"Expected file at {SERVICE_ACCOUNT_FILE}"
        )
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return gspread.authorize(credentials)


def _resolve_worksheet(client: gspread.Client) -> gspread.Worksheet:
    """Open or create the worksheet configured for recruiter leads."""
    if SHEET_ID:
        sheet = client.open_by_key(SHEET_ID)
    else:
        try:
            sheet = client.open(SHEET_TITLE)
        except SpreadsheetNotFound:
            sheet = client.create(SHEET_TITLE)
            logger.info("Created new spreadsheet titled '%s'", SHEET_TITLE)

    try:
        return sheet.worksheet(WORKSHEET_NAME)
    except WorksheetNotFound:
        return sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=10)


def log_recruiter_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Append a recruiter lead entry to the configured Google Sheet."""
    required_keys = {"recruiter_name", "company", "role", "contact", "notes"}
    missing = required_keys - set(lead.keys())
    if missing:
        raise ValueError(f"Missing required lead fields: {', '.join(sorted(missing))}")

    client = _get_gspread_client()
    worksheet = _resolve_worksheet(client)

    timestamp = datetime.utcnow().isoformat()
    row = [
        timestamp,
        lead.get("recruiter_name", ""),
        lead.get("company", ""),
        lead.get("role", ""),
        lead.get("contact", ""),
        lead.get("notes", ""),
    ]
    worksheet.append_row(row, value_input_option="USER_ENTERED")
    logger.info("Recruiter lead logged at %s", timestamp)
    return {"status": "success", "timestamp": timestamp, "worksheet": worksheet.title}
