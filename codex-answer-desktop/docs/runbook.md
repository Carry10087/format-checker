# Runbook

## Backend only

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

## Desktop only

The desktop app expects the backend on `http://127.0.0.1:8765`.

```powershell
cd desktop
npm.cmd install
npm.cmd start
```

## One-click Windows launcher

From the project root:

```powershell
start.cmd
```

`start.cmd` will:

- create `backend/.venv` if it does not exist
- install backend and desktop dependencies if they are missing
- auto-detect a formatter skill from `../answer-format-rules/SKILL.md` first
- load overrides from `start.local.cmd` when present

## Environment Variables

- `CODEX_AGENT_API_URL`: OpenAI-compatible chat completions endpoint
- `CODEX_AGENT_API_KEY`: API key for the endpoint
- `CODEX_AGENT_MODEL`: model name, default `gpt-5.2`
- `CODEX_SKILL_PATH`: optional override for the strict formatter skill path
- `CODEX_LOCAL_KB_ROOTS`: semicolon-separated extra local knowledge roots

## Data

Runtime data is stored in `backend/.data/`:

- `config.json`
- `history.json`

These files are local-only and safe to delete during development.
