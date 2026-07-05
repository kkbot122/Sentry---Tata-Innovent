from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class CwruSelection:
    filename: str
    label: str
    severity: str
    fault_type: str
    fault_size_inches: float | None
    sample_rate_hz: int
    rpm: int
    signal_key: str


SELECTED_CWRU_FILES: tuple[CwruSelection, ...] = (
    CwruSelection(
        filename="97_Normal_0hp_1797rpm.mat",
        label="Healthy",
        severity="normal",
        fault_type="none",
        fault_size_inches=None,
        sample_rate_hz=12_000,
        rpm=1797,
        signal_key="X097_DE_time",
    ),
    CwruSelection(
        filename="105_IR007_0hp_1797rpm.mat",
        label="Warning",
        severity="mild",
        fault_type="inner_race",
        fault_size_inches=0.007,
        sample_rate_hz=12_000,
        rpm=1797,
        signal_key="X105_DE_time",
    ),
    CwruSelection(
        filename="209_IR021_0hp_1797rpm.mat",
        label="Critical",
        severity="severe",
        fault_type="inner_race",
        fault_size_inches=0.021,
        sample_rate_hz=12_000,
        rpm=1797,
        signal_key="X209_DE_time",
    ),
)


def load_drive_end_signal(selection: CwruSelection) -> np.ndarray:
    path = RAW_DATA_DIR / selection.filename
    mat_file = loadmat(path)

    if selection.signal_key not in mat_file:
        available = sorted(key for key in mat_file if not key.startswith("__"))
        raise KeyError(
            f"{selection.signal_key} not found in {path.name}. Available keys: {available}"
        )

    return np.asarray(mat_file[selection.signal_key], dtype=float).ravel()
