from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.features import FEATURE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_PATH = PROJECT_ROOT / "models" / "feature_baseline.json"


@dataclass(frozen=True)
class FeatureDeviation:
    feature: str
    value: float
    baseline_mean: float
    baseline_std: float
    z_score: float


def load_feature_baseline(path: Path = DEFAULT_BASELINE_PATH) -> dict[str, dict[str, float]]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_top_deviation(
    features: dict[str, float],
    baseline: dict[str, dict[str, float]],
) -> FeatureDeviation:
    deviations: list[FeatureDeviation] = []

    for feature in FEATURE_COLUMNS:
        stats = baseline[feature]
        value = float(features[feature])
        mean = float(stats["mean"])
        std = float(stats["std"])
        scale = max(std, abs(mean) * 0.05, 1e-9)
        z_score = abs(value - mean) / scale

        deviations.append(
            FeatureDeviation(
                feature=feature,
                value=value,
                baseline_mean=mean,
                baseline_std=std,
                z_score=float(z_score),
            )
        )

    return max(deviations, key=lambda deviation: deviation.z_score)


def recommendation_for(prediction: str, top_deviation: FeatureDeviation) -> str:
    if prediction == "Healthy":
        return "System operating within healthy vibration baseline. Continue monitoring."

    feature_recommendations = {
        "rms": "Overall vibration energy is elevated. Inspect bearing load, alignment, and mounting.",
        "std": "Signal variability is elevated. Check for looseness, imbalance, or early vibration instability.",
        "kurtosis": "Impulsive vibration is elevated. Inspect bearing surfaces for localized pitting or impacts.",
        "dominant_freq_hz": "Dominant frequency has shifted. Compare bearing fault frequency against shaft speed and inspect rotating components.",
        "spectral_energy": "Frequency-domain energy is elevated. Inspect bearing assembly for mechanical degradation.",
    }
    base = feature_recommendations.get(
        top_deviation.feature,
        "Inspect the bearing assembly and schedule maintenance review.",
    )

    if prediction == "Warning":
        return f"Warning state detected. {base}"
    if prediction == "Critical":
        return f"Critical state detected. Stop or reduce machine load and inspect immediately. {base}"

    return base
