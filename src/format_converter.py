import json
from timecode_utils import TimecodeUtils

class SubtitleFormatConverter:
    """
    Handles conversion between different subtitle formats.
    """
    @staticmethod
    def convert_json_to_srt(json_path: str, frame_rate: float, offset_frames: int = 0) -> str:
        """
        Reads a JSON file with subtitle data and converts it into an SRT formatted string.

        Args:
            json_path (str): The path to the input JSON file.
            frame_rate (float): The frame rate of the timeline.
            offset_frames (int): The number of frames to offset the timecodes by.
                                 Used to create zero-based timecodes from an absolute timeline.

        Returns:
            str: A string containing the subtitles in SRT format.
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                subtitles = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing JSON file: {e}")
            return ""

        srt_content = []
        for i, sub in enumerate(subtitles):
            try:
                # Convert to frames and then apply the offset to make it zero-based
                start_frames = TimecodeUtils.timecode_to_frames(sub['start'], frame_rate) - offset_frames
                end_frames = TimecodeUtils.timecode_to_frames(sub['end'], frame_rate) - offset_frames

                # Ensure frames are not negative after offset
                start_frames = max(0, start_frames)
                end_frames = max(0, end_frames)

                start_time = TimecodeUtils.timecode_to_srt_format(start_frames, frame_rate)
                end_time = TimecodeUtils.timecode_to_srt_format(end_frames, frame_rate)

                srt_content.append(f"{i + 1}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(sub['text'])
                srt_content.append("")  # Add a blank line after each entry
            except (KeyError, ValueError) as e:
                print(f"Skipping invalid subtitle entry at index {i}: {e}")
                continue
                
        return "\n".join(srt_content)