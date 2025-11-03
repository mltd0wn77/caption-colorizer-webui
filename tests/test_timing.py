from captions.timing import ms_to_frames


def test_ms_to_frames_basic():
    info = ms_to_frames(0, 1000, fps=30)
    assert info.in_frame == 0
    assert info.out_frame == 30
    assert info.duration_frames == 30


# end_ms equal to start_ms so rounded frames would be equal without enforcement
def test_ms_to_frames_min_duration():
    info = ms_to_frames(0, 0, fps=30)
    # Should enforce at least 2-frame duration
    assert info.out_frame - info.in_frame >= 2
