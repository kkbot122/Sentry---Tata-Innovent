from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.decision_logic import (
    FeatureDeviation,
    find_top_deviation,
    load_feature_baseline,
    recommendation_for,
)
from app.features import FEATURE_COLUMNS, extract_feature_vector
from app.replay import BearingSignalReplay, ReplayChunk


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "bearing_rf_model.joblib"


@dataclass(frozen=True)
class InferenceResult:
    timestamp: str
    replay_state: str
    prediction: str
    confidence: float
    latency_ms: float
    top_deviation: FeatureDeviation
    recommendation: str
    features: dict[str, float]
    source_file: str
    chunk_index: int
    signal: list[float]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence_percent"] = round(self.confidence * 100, 2)
        return payload

    def log_line(self) -> str:
        return (
            f"{self.timestamp} chunk={self.chunk_index:03d} "
            f"replay={self.replay_state:8s} prediction={self.prediction:8s} "
            f"confidence={self.confidence:.3f} latency_ms={self.latency_ms:.3f} "
            f"top_deviation={self.top_deviation.feature}"
        )


class EdgeInferenceEngine:
    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        baseline_path: Path | None = None,
    ) -> None:
        payload = joblib.load(model_path)
        self.model = payload["model"]
        self.feature_columns = tuple(payload.get("feature_columns", FEATURE_COLUMNS))
        self.classes = list(payload.get("classes", self.model.classes_))
        self.baseline = load_feature_baseline() if baseline_path is None else load_feature_baseline(baseline_path)

        if self.feature_columns != FEATURE_COLUMNS:
            raise ValueError(
                "Saved model feature columns do not match shared FEATURE_COLUMNS: "
                f"{self.feature_columns} != {FEATURE_COLUMNS}"
            )

    def predict_chunk(self, chunk: ReplayChunk) -> InferenceResult:
        feature_vector = extract_feature_vector(
            chunk.signal,
            chunk.sample_rate_hz,
            self.feature_columns,
        )
        model_input = pd.DataFrame(feature_vector.model_input, columns=self.feature_columns)

        started_at = time.perf_counter()
        prediction = str(self.model.predict(model_input)[0])
        probabilities = self.model.predict_proba(model_input)[0]
        latency_ms = (time.perf_counter() - started_at) * 1000

        confidence = float(max(probabilities))
        top_deviation = find_top_deviation(feature_vector.values, self.baseline)
        recommendation = recommendation_for(prediction, top_deviation)

        return InferenceResult(
            timestamp=chunk.timestamp,
            replay_state=chunk.state,
            prediction=prediction,
            confidence=confidence,
            latency_ms=float(latency_ms),
            top_deviation=top_deviation,
            recommendation=recommendation,
            features=feature_vector.values,
            source_file=chunk.source_file,
            chunk_index=chunk.chunk_index,
            signal=chunk.signal,
        )


def run_preview(limit: int) -> None:
    engine = EdgeInferenceEngine()
    replay = BearingSignalReplay()

    for index, chunk in enumerate(replay.iter_chunks()):
        result = engine.predict_chunk(chunk)
        print(result.log_line())
        print(f"  recommendation={result.recommendation}")
        if index + 1 >= limit:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview local edge inference results.")
    parser.add_argument("--limit", type=int, default=12, help="Number of replay chunks to process.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final result as JSON for payload inspection.",
    )
    args = parser.parse_args()

    if not args.json:
        run_preview(args.limit)
        return

    engine = EdgeInferenceEngine()
    result = None
    for index, chunk in enumerate(BearingSignalReplay().iter_chunks()):
        result = engine.predict_chunk(chunk)
        if index + 1 >= args.limit:
            break

    print(json.dumps(result.to_dict(), indent=2) if result else "{}")


if __name__ == "__main__":
    main()
