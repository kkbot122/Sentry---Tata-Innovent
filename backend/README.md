# Bearing Fault Backend

FastAPI backend for the Phase 1 bearing-fault demo.

## Setup

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The initial health endpoint is available at `GET /health`.
