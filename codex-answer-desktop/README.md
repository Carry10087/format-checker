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
   npm.cmd install
   ```

3. Configure environment variables for your model endpoint:

   ```powershell
   $env:CODEX_AGENT_API_URL="http://127.0.0.1:9000/v1/chat/completions"
   $env:CODEX_AGENT_API_KEY="your-key"
   $env:CODEX_AGENT_MODEL="gpt-5.2"
   ```

4. Start the desktop app:

   ```powershell
   npm.cmd start
   ```

## One-Click Start on Windows

You can now launch the app by double-clicking `start.cmd`.

- On the first run, it will create the backend virtual environment and install missing dependencies automatically.
- It will auto-detect the formatter skill from `../answer-format-rules/SKILL.md` first, then fall back to `~/.codex/skills/strict-answer-formatter/SKILL.md`.
- If you need to override the model endpoint, key, model name, or skill path, copy `start.local.cmd.example` to `start.local.cmd` and edit that file once.

Manual launch still works from PowerShell:

```powershell
cd desktop
npm.cmd start
```

## Skill Dependency

By default the backend reads the formatter skill from:

1. `../answer-format-rules/SKILL.md`
2. `%USERPROFILE%\.codex\skills\strict-answer-formatter\SKILL.md`

You can override it with `CODEX_SKILL_PATH`.
