from pathlib import Path
import random

import captions.parser as parser

TEST_SRT = Path(__file__).parent / "resources" / "sample.srt"


def test_parse_srt():
    caps = parser.parse_srt(TEST_SRT)
    assert len(caps) == 2
    assert caps[0].lines == ["Hello world!", "Second line"]


def test_assign_accents_no_repeats():
    caps = parser.parse_srt(TEST_SRT)
    parser.assign_accents(caps, accents_count=3, starting_index=0, rng=random.Random(42))
    prev = None
    for c in caps:
        assert c.accent_index is not None
        if prev is not None:
            assert c.accent_index != prev
        prev = c.accent_index
