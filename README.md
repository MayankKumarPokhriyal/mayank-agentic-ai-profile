# Mayank Agentic AI Profile

A fully local, agentic Streamlit application that allows recruiters to interact with Mayank Kumar Pokhriyal's professional profile, powered by Ollama (default model: `llama3`). The agent answers questions using a structured JSON memory and automatically captures hiring leads in Google Sheets when recruiter intent is detected.

## Features
- Conversational Streamlit UI that renders a first-person AI resume experience
- LLM reasoning through Ollama with deterministic tool invocation
- Structured profile memory (`profile.json`) to eliminate hallucinations
- Automated recruiter-intent detection and Google Sheets logging
- JSON-based tool responses for consistent agent behavior

## Architecture
```
Streamlit UI (app.py)
    └── Agent Orchestrator (agent.py)
            ├── Ollama llama3 local LLM
            └── Tool Layer (tools.py)
                    ├── profile.json reader
                    └── Google Sheets lead logger
```
- **app.py**: Streamlit chat interface, maintains session history, renders responses, and surfaces recruiter lead confirmations.
- **agent.py**: Orchestrates conversation loops with Ollama, parses JSON actions, calls tools, and enforces first-person voice.
- **tools.py**: Handles structured profile lookups and Google Sheets logging with a local service account credential.
- **profile.json**: Authoritative professional data store for skills, education, experience, projects, and preferences.

## Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed locally and running (`ollama serve`)
- `llama3` (or another compatible) model pulled: `ollama pull llama3`
- Google Cloud service account with Sheets & Drive scopes and a `service_account.json` placed at the project root

## Setup
1. **Clone & enter project**
   ```bash
   git clone https://github.com/mayankkumarpokhriyal/mayank-agentic-ai-profile.git
   cd mayank-agentic-ai-profile
   ```
2. **Create & activate a virtual environment (recommended)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Ollama Configuration
1. Start the Ollama server if it is not already running:
   ```bash
   ollama serve
   ```
2. Pull the desired model (defaults to `llama3`):
   ```bash
   ollama pull llama3
   ```
3. Optional environment variables:
   - `OLLAMA_MODEL`: Override the model name (e.g., `mayank-llama3`)
   - `OLLAMA_HOST`: Point the client to a non-default Ollama endpoint

Ensure the environment variables are exported before launching Streamlit, for example:
```bash
export OLLAMA_MODEL=llama3
```

## Google Sheets Setup
1. Create (or identify) a Google Sheet that will store recruiter leads. The default worksheet name is `Recruiter_Leads`.
2. Generate a service account in Google Cloud and download the JSON key.
3. Share the Google Sheet with the service account email (Editor access).
4. Place `service_account.json` in the project root (same directory as `tools.py`).
5. Optional environment variables to control sheet location:
   ```bash
   export GOOGLE_SHEET_ID=<spreadsheet_id>  # Preferred: direct spreadsheet ID
   export GOOGLE_SHEET_TITLE="Recruiter Leads Workbook"  # Fallback title lookup
   export GOOGLE_WORKSHEET_NAME="Recruiter_Leads"        # Worksheet/tab name
   ```
   When `GOOGLE_SHEET_ID` is provided, it supersedes the title-based lookup and prevents ambiguity. If the
   title-based lookup is used and no spreadsheet exists yet, the service account will create one with the
   supplied title inside its Google Drive scope.

### Column Schema
`log_recruiter_lead` appends rows in the following order:
1. UTC timestamp
2. Recruiter name
3. Company
4. Role
5. Contact
6. Notes (additional context, timeline, referral info, etc.)

## Running the App
```bash
streamlit run app.py
```
The Streamlit interface opens in your browser. Chat with the AI to explore projects, experience, and availability. If recruiter interest is detected and logged, a confirmation message appears in the sidebar.

## How the Agent Works
- **Reasoning Loop**: `agent.py` sends the full conversation context and a strict system prompt to Ollama, expecting JSON responses with either a tool call or a final reply.
- **Tool Invocation**: When the model asks for `get_profile_section` or `get_project_details`, `tools.py` pulls data from `profile.json` and feeds the result back into the loop before the agent crafts a response.
- **Recruiter Detection**: The system prompt guides the model to gather recruiter details. Once all fields are present, the agent calls `log_recruiter_lead`, appends the row in Google Sheets, and confirms the capture to the user.
- **Fail-Safes**: If the agent cannot parse the model output as JSON or exceeds loop limits, a graceful fallback message is returned.

## Testing Tips
- Start Ollama and confirm connectivity with a simple script before running Streamlit.
- Validate Google Sheets access by invoking `log_recruiter_lead` directly from a Python shell with dummy data.
- Keep `profile.json` updated; the agent will never fabricate content that is not present in the JSON store.

## Project Structure
```
app.py               # Streamlit UI
agent.py             # LLM orchestration and tool loop
tools.py             # Profile and Google Sheets utilities
profile.json         # Structured professional memory
service_account.json # Google credentials (not committed)
requirements.txt     # Python dependencies
README.md            # Documentation
```

## Troubleshooting
- **Ollama errors**: Verify `ollama serve` is running and the selected model exists.
- **Sheets logging issues**: Confirm the service account has permission and the sheet ID/title is correct. Check environment variables.
- **Streamlit crashes**: Review terminal logs; missing dependencies or misconfigured credentials are common causes.

Enjoy showcasing Mayank's experience through a local, privacy-first agentic interface!
