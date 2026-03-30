# Architecture

## Goal

Create a local desktop workbench that can:

1. accept a query
2. collect evidence from public web and local knowledge
3. let a Codex-style agent decide how to use the evidence
4. produce a final answer that follows the strict formatter skill

## Components

### Desktop (`desktop/`)

- Electron window
- launches the backend automatically
- sends `run` jobs over localhost
- shows only final answers by default

### Backend (`backend/`)

- FastAPI server
- query orchestration
- mixed retrieval
- skill loading
- model invocation
- local history and config persistence

### Retrieval

- `WebRetriever`: fetches public search results and extracts compact article text
- `LocalKnowledgeRetriever`: searches skill files, docs, and configured local roots
- `merge_sources`: deduplicates and normalizes results

### Agent

- classifies query shape heuristically
- loads the formatter skill
- converts normalized evidence into note-style source blocks
- sends the full task to a compatible model endpoint

## Why this shape

- Electron gives a real desktop shell without touching the existing Streamlit app
- Python keeps your existing logic ecosystem and makes retrieval/model code easy to reuse
- the skill remains the single source of truth for formatting behavior
