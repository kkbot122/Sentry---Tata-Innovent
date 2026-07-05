from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from scipy.stats import kurtosis


FEATURE_COLUMNS = (
    "rms",
    "std",
    "kurtosis",
    "dominant_freq_hz",
    "spectral_energy",
)


@dataclass(frozen=True)
class FeatureVector:
    values: dict[str, float]
    model_input: np.ndarray


def extract_features(signal_window: np.ndarray, sample_rate_hz: int) -> dict[str, float]:
    signal = np.asarray(signal_window, dtype=float).ravel()
    if signal.size == 0:
        raise ValueError("signal_window must contain at least one sample")

    centered = signal - np.mean(signal)
    fft_values = np.fft.rfft(centered)
    fft_freqs = np.fft.rfftfreq(signal.size, d=1.0 / sample_rate_hz)
    magnitudes = np.abs(fft_values)

    if magnitudes.size > 1:
        dominant_index = int(np.argmax(magnitudes[1:]) + 1)
        dominant_freq_hz = float(fft_freqs[dominant_index])
    else:
        dominant_freq_hz = 0.0

    return {
        "rms": float(np.sqrt(np.mean(np.square(signal)))),
        "std": float(np.std(signal)),
        "kurtosis": float(kurtosis(signal, fisher=False, bias=False)),
        "dominant_freq_hz": dominant_freq_hz,
        "spectral_energy": float(np.sum(np.square(magnitudes)) / signal.size),
    }


def features_to_model_input(
    features: Mapping[str, float],
    feature_columns: tuple[str, ...] = FEATURE_COLUMNS,
) -> np.ndarray:
    missing_features = [feature for feature in feature_columns if feature not in features]
    if missing_features:
        joined_features = ", ".join(missing_features)
        raise KeyError(f"Missing model features: {joined_features}")

    return np.array(
        [[float(features[feature]) for feature in feature_columns]],
        dtype=float,
    )


def extract_feature_vector(
    signal_window: np.ndarray,
    sample_rate_hz: int,
    feature_columns: tuple[str, ...] = FEATURE_COLUMNS,
) -> FeatureVector:
    values = extract_features(signal_window, sample_rate_hz)
    return FeatureVector(
        values=values,
        model_input=features_to_model_input(values, feature_columns),
    )


def window_signal(
    signal: np.ndarray,
    window_size: int,
    step_size: int,
) -> list[np.ndarray]:
    values = np.asarray(signal, dtype=float).ravel()
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    if step_size <= 0:
        raise ValueError("step_size must be positive")
    if values.size < window_size:
        return []

    return [
        values[start : start + window_size]
        for start in range(0, values.size - window_size + 1, step_size)
    ]
