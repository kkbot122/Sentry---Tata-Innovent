from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np

from app.cwru_dataset import CwruSelection, SELECTED_CWRU_FILES, load_drive_end_signal


DEFAULT_CHUNK_SIZE = 2048
DEFAULT_INTERVAL_SECONDS = 0.2


@dataclass(frozen=True)
class ReplaySegment:
    selection: CwruSelection
    chunks: int


@dataclass(frozen=True)
class ReplayChunk:
    timestamp: str
    state: str
    severity: str
    fault_type: str
    source_file: str
    signal_key: str
    sample_rate_hz: int
    rpm: int
    chunk_index: int
    segment_index: int
    start_sample: int
    end_sample: int
    signal: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "state": self.state,
            "severity": self.severity,
            "fault_type": self.fault_type,
            "source_file": self.source_file,
            "signal_key": self.signal_key,
            "sample_rate_hz": self.sample_rate_hz,
            "rpm": self.rpm,
            "chunk_index": self.chunk_index,
            "segment_index": self.segment_index,
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "signal": self.signal,
        }


def default_demo_segments(
    healthy_chunks: int = 12,
    warning_chunks: int = 10,
    critical_chunks: int = 10,
) -> list[ReplaySegment]:
    selections_by_label = {selection.label: selection for selection in SELECTED_CWRU_FILES}
    return [
        ReplaySegment(selections_by_label["Healthy"], healthy_chunks),
        ReplaySegment(selections_by_label["Warning"], warning_chunks),
        ReplaySegment(selections_by_label["Critical"], critical_chunks),
    ]


class BearingSignalReplay:
    def __init__(
        self,
        segments: list[ReplaySegment] | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        loop_signals: bool = True,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        self.segments = segments or default_demo_segments()
        self.chunk_size = chunk_size
        self.loop_signals = loop_signals
        self._signals = {
            segment.selection.filename: load_drive_end_signal(segment.selection)
            for segment in self.segments
        }

    def iter_chunks(self) -> Iterator[ReplayChunk]:
        chunk_index = 0

        for segment_index, segment in enumerate(self.segments):
            signal = self._signals[segment.selection.filename]

            for segment_chunk_index in range(segment.chunks):
                start_sample = segment_chunk_index * self.chunk_size
                raw_chunk = self._slice_signal(signal, start_sample)

                yield ReplayChunk(
                    timestamp=datetime.now(UTC).isoformat(),
                    state=segment.selection.label,
                    severity=segment.selection.severity,
                    fault_type=segment.selection.fault_type,
                    source_file=segment.selection.filename,
                    signal_key=segment.selection.signal_key,
                    sample_rate_hz=segment.selection.sample_rate_hz,
                    rpm=segment.selection.rpm,
                    chunk_index=chunk_index,
                    segment_index=segment_index,
                    start_sample=start_sample % signal.size,
                    end_sample=(start_sample + raw_chunk.size) % signal.size,
                    signal=raw_chunk.tolist(),
                )
                chunk_index += 1

    async def stream(
        self,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    ) -> AsyncIterator[ReplayChunk]:
        if interval_seconds < 0:
            raise ValueError("interval_seconds cannot be negative")

        for chunk in self.iter_chunks():
            yield chunk
            if interval_seconds:
                await asyncio.sleep(interval_seconds)

    def _slice_signal(self, signal: np.ndarray, start_sample: int) -> np.ndarray:
        if signal.size < self.chunk_size and not self.loop_signals:
            raise ValueError("signal is shorter than chunk_size")

        start = start_sample % signal.size
        end = start + self.chunk_size

        if end <= signal.size:
            return signal[start:end]

        if not self.loop_signals:
            return signal[start:]

        overflow = end - signal.size
        return np.concatenate([signal[start:], signal[:overflow]])


async def preview_replay(limit: int, interval_seconds: float) -> None:
    replay = BearingSignalReplay()
    emitted = 0

    async for chunk in replay.stream(interval_seconds=interval_seconds):
        print(
            f"{chunk.chunk_index:03d} {chunk.timestamp} "
            f"{chunk.state:8s} samples={len(chunk.signal)} "
            f"source={chunk.source_file}"
        )
        emitted += 1
        if emitted >= limit:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview the CWRU demo replay stream.")
    parser.add_argument("--limit", type=int, default=8, help="Number of chunks to print.")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Delay in seconds between emitted chunks.",
    )
    args = parser.parse_args()

    asyncio.run(preview_replay(limit=args.limit, interval_seconds=args.interval))


if __name__ == "__main__":
    main()
