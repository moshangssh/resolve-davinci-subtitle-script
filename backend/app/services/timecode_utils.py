# timecode_utils.py
"""
A static utility class for handling timecode conversions using the 'timecode' library.
This module simplifies the process of converting between timecode strings, frame counts,
and SRT time formats. All methods are static and do not require an instance of the class.
"""
from timecode import Timecode

class TimecodeUtils:
    """A collection of static methods for timecode conversion."""

    @staticmethod
    def frame_from_timecode(timecode_str: str, frame_rate: float, drop_frame: bool = None) -> int:
        """
        Converts a timecode string (e.g., '01:00:00:00' or '01:00:00;00') to the total number of frames.
        The `timecode` library automatically infers the drop-frame status from the separator (':' vs ';').
        The `drop_frame` parameter is kept for explicit control if needed, but is often redundant.
        """
        try:
            tc = Timecode(frame_rate, timecode_str)
            # Explicitly set drop_frame if provided, as the library might infer otherwise.
            if drop_frame is not None:
                tc.drop_frame = drop_frame
            return tc.frames - 1
        except Exception as e:
            raise ValueError(f"Invalid timecode or parameters: {e}")

    @staticmethod
    def timecode_from_frame(frame: int, frame_rate: float, drop_frame: bool = False) -> str:
        """Converts a total frame count to a timecode string."""
        if frame < 0:
            raise ValueError("Frame number cannot be negative.")

        try:
            # The 'timecode' library is 1-based, so we add 1 to our 0-based frame count.
            tc = Timecode(frame_rate, frames=frame + 1)
            tc.drop_frame = drop_frame
            return str(tc)
        except Exception as e:
            # Catch potential errors from the timecode library.
            raise ValueError(f"Invalid frame count or parameters: {e}")

    @staticmethod
    def timecode_to_srt_format(frame: int, frame_rate: float) -> str:
        """Converts total frames to an SRT timecode string (HH:MM:SS,ms)."""
        if frame_rate <= 0:
            return "00:00:00,000"
        
        frame = max(0, int(frame))

        if frame == 0:
            return "00:00:00,000"

        # Total seconds can be calculated directly without creating a Timecode object first.
        # This is more direct and avoids potential library overhead for a simple calculation.
        total_seconds = frame / frame_rate
        
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds_float = divmod(remainder, 60)
        seconds = int(seconds_float)
        milliseconds = int((seconds_float - seconds) * 1000)

        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"

    @staticmethod
    def timecode_to_frames(srt_time: str, frame_rate: float) -> int:
        """Converts an SRT timecode string (HH:MM:SS,ms) to total frames."""
        try:
            time_part, ms_part = srt_time.replace('.', ',').split(',')
            h, m, s = map(int, time_part.split(':'))
            
            total_seconds = h * 3600 + m * 60 + s + (int(ms_part) / 1000.0)
            
            # Calculate total frames by multiplying total seconds by the frame rate.
            # Round to the nearest integer to get the closest frame number.
            return int(round(total_seconds * frame_rate))
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid SRT time format '{srt_time}'. Expected HH:MM:SS,ms. Original error: {e}")