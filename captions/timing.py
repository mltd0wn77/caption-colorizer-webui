from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

@dataclass
class FrameInfo:
    in_frame: int
    out_frame: int
    fps_num: int
    fps_den: int

    @property
    def duration_frames(self) -> int:
        return self.out_frame - self.in_frame

def ms_to_frames(start_ms: int, end_ms: int, fps_num: int, fps_den: int) -> FrameInfo:
    """
    Converts millisecond timestamps to frame counts using precise Decimal arithmetic.
    """
    fps = Decimal(fps_num) / Decimal(fps_den)
    
    # Calculate start and end frames
    start_frame = int(((Decimal(start_ms) / 1000) * fps).to_integral_value(ROUND_HALF_UP))
    end_frame = int(((Decimal(end_ms) / 1000) * fps).to_integral_value(ROUND_HALF_UP))
    
    if end_frame <= start_frame:
        end_frame = start_frame + 2  # Enforce minimum 2-frame duration
        
    return FrameInfo(start_frame, end_frame, fps_num, fps_den)

__all__ = ["ms_to_frames", "FrameInfo"]
