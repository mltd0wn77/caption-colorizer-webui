from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence
import math
import random

import pysrt


@dataclass
class Caption:
    index: int
    start_ms: int
    end_ms: int
    lines: List[str]
    accent_index: int | None = None
    chosen_line: int | None = None  # for two-line blocks
    words_colored: int | None = None  # count of words accented

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


# ----------------------------- Parsing ------------------------------------ #

def _to_ms(ts: pysrt.SubRipTime) -> int:
    """Convert a pysrt time to milliseconds."""
    return (ts.hours * 3600 + ts.minutes * 60 + ts.seconds) * 1000 + ts.milliseconds


def parse_srt(srt_path: Path) -> List[Caption]:
    """Return list of Caption objects preserving order from the SRT file."""
    subs = pysrt.open(str(srt_path), encoding="utf-8-sig")
    captions: List[Caption] = []
    for item in subs:
        lines = [line.rstrip("\n") for line in item.text.split("\n")]
        captions.append(
            Caption(
                index=int(item.index),
                start_ms=_to_ms(item.start),
                end_ms=_to_ms(item.end),
                lines=lines,
            )
        )
    return captions


# --------------------------- Accent Logic --------------------------------- #

def assign_accents(
    captions: List[Caption],
    accents_count: int,
    starting_index: int,
    rng: random.Random,
):
    """Mutate captions adding accent_index, chosen_line, words_colored according to rules."""
    if accents_count < 1:
        raise ValueError("At least one accent color is required")

    prev = None
    for i, cap in enumerate(captions):
        # Select accent index
        if accents_count == 1:
            acc_idx = 0
        elif i == 0:
            acc_idx = starting_index % accents_count
        else:
            choices = [x for x in range(accents_count) if x != prev]
            acc_idx = rng.choice(choices)
        cap.accent_index = acc_idx
        prev = acc_idx

        # Determine coloring strategy
        if len(cap.lines) == 2:
            chosen_line = rng.choice([0, 1])
            cap.chosen_line = chosen_line
            words_colored = len(cap.lines[chosen_line].split())
            cap.words_colored = words_colored
        else:
            words = cap.lines[0].split()
            words_colored = math.ceil(len(words) / 2)
            cap.words_colored = words_colored
            cap.chosen_line = 0


__all__ = [
    "Caption",
    "parse_srt",
    "assign_accents",
]
