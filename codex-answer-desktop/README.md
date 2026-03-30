# Codex Answer Desktop

A Windows-first internal desktop app that combines:

- Electron desktop UI
- Python local backend
- mixed retrieval from public web and local knowledge
- strict answer generation powered by a Codex-style agent flow

The app is designed to keep your existing Streamlit project untouched. Everything in this folder is independent.

## Structure

- `desktop/`: Electron shell and UI
- `backend/`: FastAPI service, retrieval pipeline, agent orchestration, local storage
- `docs/`: architecture and run guides

## Quick Start

1. Install backend dependencies:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Install desktop dependencies:

   ```powershell
   cd ..\desktop
   npm install
   ```

3. Configure environment variables for your model endpoint:

   ```powershell
   $env:CODEX_AGENT_API_URL="http://127.0.0.1:9000/v1/chat/completions"
   $env:CODEX_AGENT_API_KEY="your-key"
   $env:CODEX_AGENT_MODEL="gpt-5.2"
   ```

4. Start the desktop app:

   ```powershell
   npm start
   ```

## Skill Dependency

By default the backend reads the formatter skill from:

`C:\Users\EDY\.codex\skills\strict-answer-formatter\SKILL.md`

You can override it with `CODEX_SKILL_PATH`.
