# Snapdeal Virtual KAM (demo)

A LangGraph Virtual Key Account Manager for a Snapdeal seller, using a local
Ollama model and an in-memory mock seller dataset.

## Setup

```bash
ollama serve
ollama pull qwen2.5:3b
uv sync
```

## Run

```bash
uv run python -m seller_dashboard.bot
```

Optional environment variables:

- `OLLAMA_MODEL` - installed Ollama model to use (default: `qwen2.5:3b`).
- `THREAD_ID` - conversation thread ID (default: `demo-session-1`).
