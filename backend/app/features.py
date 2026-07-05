from __future__ import annotations

import numpy as np
from scipy.stats import kurtosis


FEATURE_COLUMNS = [
    "rms",
    "std",
    "kurtosis",
    "dominant_freq_hz",
    "spectral_energy",
]


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
