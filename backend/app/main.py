from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.inference import EdgeInferenceEngine
from app.replay import BearingSignalReplay, DEFAULT_INTERVAL_SECONDS


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.inference_engine = EdgeInferenceEngine()
    yield


app = FastAPI(title="Bearing Fault Demo API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_loaded": hasattr(app.state, "inference_engine"),
        "websocket": "/ws/live",
    }


@app.websocket("/ws/live")
async def live_stream(
    websocket: WebSocket,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
) -> None:
    await websocket.accept()

    engine: EdgeInferenceEngine = websocket.app.state.inference_engine
    replay = BearingSignalReplay()

    try:
        async for chunk in replay.stream(interval_seconds=interval_seconds):
            result = engine.predict_chunk(chunk)
            print(result.log_line(), flush=True)
            await websocket.send_json(result.to_dict())
    except WebSocketDisconnect:
        print("Dashboard WebSocket disconnected.", flush=True)
