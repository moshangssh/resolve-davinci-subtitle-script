# tests/test_timecode_utils.py
import pytest
from src.timecode_utils import TimecodeUtils

# --- Test cases for frame_from_timecode ---
@pytest.mark.parametrize("timecode_str, frame_rate, expected_frames", [
    ("00:00:01:00", 24, 24),
    ("01:00:00:00", 25, 90000),
    ("00:00:00:00", 30, 0),
    ("10:00:00:00", 23.976, 863136),
    ("00:01:00;02", 29.97, 1798),
    ("00:10:00;00", 29.97, 17982),
])
def test_frame_from_timecode(timecode_str, frame_rate, expected_frames):
    """Test frame_from_timecode converts various timecode formats to frame counts."""
    assert TimecodeUtils.frame_from_timecode(timecode_str, frame_rate) == expected_frames

def test_frame_from_timecode_invalid():
    """Test frame_from_timecode with invalid input."""
    with pytest.raises(ValueError, match="Invalid timecode or parameters"):
        TimecodeUtils.frame_from_timecode("invalid-timecode", 24)

# --- Test cases for timecode_from_frame ---
@pytest.mark.parametrize("frames, frame_rate, drop_frame, expected_timecode_str", [
    (24, 24, False, "00:00:01:00"),
    (90000, 25, False, "01:00:00:00"),
    (0, 30, False, "00:00:00:00"),
    (1, 24, False, "00:00:00:01"),
    (1798, 29.97, True, "00:01:00;02"),
    (17982, 29.97, True, "00:10:00;00"),
])
def test_timecode_from_frame(frames, frame_rate, drop_frame, expected_timecode_str):
    """Test timecode_from_frame converts frame counts to timecode strings."""
    assert TimecodeUtils.timecode_from_frame(frames, frame_rate, drop_frame) == expected_timecode_str

def test_timecode_from_frame_negative_input():
    """Test timecode_from_frame with a negative frame number, which should raise a ValueError."""
    with pytest.raises(ValueError):
         TimecodeUtils.timecode_from_frame(-10, 24, False)

# --- Test cases for timecode_to_srt_format ---
@pytest.mark.parametrize("frame, frame_rate, expected_srt", [
    (0, 24, "00:00:00,000"),
    (24, 24, "00:00:01,000"),
    (120, 60, "00:00:02,000"),
    (144, 24, "00:00:06,000"),
    (863136, 23.976, "10:00:00,000"),
    (1798, 29.97, "00:00:59,993"), # Note: floating point precision
    (-100, 24, "00:00:00,000"), # Negative frames should be treated as 0
    (100, 0, "00:00:00,000"), # Zero frame rate should not crash
])
def test_timecode_to_srt_format(frame, frame_rate, expected_srt):
    """Test timecode_to_srt_format with various inputs."""
    assert TimecodeUtils.timecode_to_srt_format(frame, frame_rate) == expected_srt


# --- Test cases for timecode_to_frames ---
@pytest.mark.parametrize("srt_time, frame_rate, expected_frames", [
    ("00:00:00,000", 24, 0),
    ("00:00:01,000", 24, 24),
    ("00:00:02,000", 60, 120),
    ("00:00:06,000", 24, 144),
    ("10:00:00,000", 23.976, 863136),
    ("00:00:59,993", 29.97, 1798),
    ("00:00:00.500", 24, 12), # Test with a dot separator
])
def test_timecode_to_frames(srt_time, frame_rate, expected_frames):
    """Test timecode_to_frames with various SRT time formats."""
    assert TimecodeUtils.timecode_to_frames(srt_time, frame_rate) == expected_frames

def test_timecode_to_frames_invalid_format():
    """Test timecode_to_frames with invalid SRT format."""
    with pytest.raises(ValueError):
        TimecodeUtils.timecode_to_frames("not,a,timecode", 24)

    with pytest.raises(ValueError):
        TimecodeUtils.timecode_to_frames("00:00:00", 24) # Missing milliseconds
