import json
import re
from src.timecode_utils import TimecodeUtils

def format_subtitles_to_srt(subtitles: list, frame_rate: float, offset_frames: int = 0) -> str:
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

def convert_json_to_srt(json_path: str, frame_rate: float, offset_frames: int = 0) -> str:
    """
    Reads a JSON file with subtitle data and converts it into an SRT formatted string.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            subtitles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing JSON file: {e}")
        return ""

    return format_subtitles_to_srt(subtitles, frame_rate, offset_frames)

def parse_srt_content(srt_content: str) -> list:
    """Parses SRT content into a list of subtitle dictionaries."""
    subtitle_blocks = srt_content.strip().split('\n\n')
    subtitles = []
    for block in subtitle_blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0])
                time_line = lines[1]
                text_lines = lines[2:]
                
                start_str, end_str = [t.strip() for t in time_line.split('-->')]
                
                subtitles.append({
                    'index': index,
                    'start': start_str,
                    'end': end_str,
                    'text': '\n'.join(text_lines)
                })
            except (ValueError, IndexError) as e:
                print(f"Skipping invalid SRT block: {block} - Error: {e}")
                continue
    return subtitles