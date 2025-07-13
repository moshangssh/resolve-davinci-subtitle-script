# tests/test_format_converter.py
import pytest
import json
import os
from unittest.mock import patch, mock_open

from src.format_converter import format_subtitles_to_srt, convert_json_to_srt
from src.timecode_utils import TimecodeUtils

# --- Mocks and Fixtures ---

@pytest.fixture
def mock_timecode_utils():
    """Fixture to mock the TimecodeUtils methods."""
    with patch('format_converter.TimecodeUtils', autospec=True) as mock_tc:
        # Simulate the conversion logic for testing purposes
        def mock_timecode_to_frames(timecode, frame_rate):
            parts = timecode.split(':')
            h, m, s_ms = int(parts[0]), int(parts[1]), float(parts[2].replace(',', '.'))
            return int((h * 3600 + m * 60 + s_ms) * frame_rate)

        def mock_timecode_to_srt_format(frames, frame_rate):
            total_seconds = frames / frame_rate
            h = int(total_seconds / 3600)
            m = int((total_seconds % 3600) / 60)
            s = int(total_seconds % 60)
            ms = int((total_seconds - int(total_seconds)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        mock_tc.timecode_to_frames.side_effect = mock_timecode_to_frames
        mock_tc.timecode_to_srt_format.side_effect = mock_timecode_to_srt_format
        yield mock_tc

# --- Tests for format_subtitles_to_srt ---

def test_format_subtitles_to_srt_basic(mock_timecode_utils):
    """Test basic conversion from a list of subtitles to SRT format."""
    subtitles = [
        {'start': '00:00:01,000', 'end': '00:00:02,500', 'text': 'Hello world.'},
        {'start': '00:00:03,000', 'end': '00:00:05,000', 'text': 'This is a test.'}
    ]
    frame_rate = 24.0
    expected_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "Hello world.\n\n"
        "2\n"
        "00:00:03,000 --> 00:00:05,000\n"
        "This is a test."
    )
    
    result = format_subtitles_to_srt(subtitles, frame_rate)
    # Normalize line endings for comparison
    assert result.strip().replace('\r\n', '\n') == expected_srt.strip().replace('\r\n', '\n')

def test_format_subtitles_to_srt_with_offset(mock_timecode_utils):
    """Test conversion with a frame offset to make timecodes zero-based."""
    subtitles = [
        {'start': '01:00:01,000', 'end': '01:00:02,500', 'text': 'First line.'}
    ]
    frame_rate = 24.0
    # Offset equivalent to 1 hour
    offset_frames = int(3600 * frame_rate)
    
    expected_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "First line."
    )
    
    result = format_subtitles_to_srt(subtitles, frame_rate, offset_frames)
    assert result.strip().replace('\r\n', '\n') == expected_srt.strip().replace('\r\n', '\n')

def test_format_subtitles_to_srt_empty_list():
    """Test with an empty list of subtitles, should return an empty string."""
    assert format_subtitles_to_srt([], 24.0) == ""

def test_format_subtitles_to_srt_invalid_entry(mock_timecode_utils, capsys):
    """Test that invalid subtitle entries are skipped gracefully."""
    subtitles = [
        {'start': '00:00:01,000', 'text': 'Missing end time.'}, # Invalid
        {'start': '00:00:03,000', 'end': '00:00:05,000', 'text': 'This is valid.'}
    ]
    frame_rate = 24.0
    
    result = format_subtitles_to_srt(subtitles, frame_rate)
    
    # Check that the valid subtitle was processed
    assert "This is valid." in result
    assert "Missing end time." not in result
    
    # Check that an error was printed for the invalid entry
    captured = capsys.readouterr()
    assert "Skipping invalid subtitle entry at index 0" in captured.out

# --- Tests for convert_json_to_srt ---

def test_convert_json_to_srt_success(mocker):
    """Test successful conversion from a JSON file path to SRT."""
    json_data = [
        {'start': '00:00:10,000', 'end': '00:00:12,000', 'text': 'From JSON file.'}
    ]
    mock_json_content = json.dumps(json_data)
    
    # Mock reading the file
    m = mock_open(read_data=mock_json_content)
    mocker.patch('builtins.open', m)
    
    # Mock the formatter function that it calls
    mocker.patch('format_converter.format_subtitles_to_srt', return_value="EXPECTED_SRT_CONTENT")
    
    result = convert_json_to_srt('fake/path/to/file.json', 24.0)
    
    # Verify file was opened correctly
    m.assert_called_once_with('fake/path/to/file.json', 'r', encoding='utf-8')
    
    # Verify the formatter was called with the correct data
    from src import format_converter
    format_converter.format_subtitles_to_srt.assert_called_once_with(json_data, 24.0, 0)
    
    assert result == "EXPECTED_SRT_CONTENT"

def test_convert_json_to_srt_file_not_found(mocker, capsys):
    """Test handling of a non-existent JSON file."""
    mocker.patch('builtins.open', side_effect=FileNotFoundError("File not found"))
    
    result = convert_json_to_srt('non/existent/file.json', 24.0)
    
    assert result == ""
    captured = capsys.readouterr()
    assert "Error reading or parsing JSON file" in captured.out

def test_convert_json_to_srt_invalid_json(mocker, capsys):
    """Test handling of a file with invalid JSON content."""
    mocker.patch('builtins.open', mock_open(read_data="{not-valid-json}"))
    
    result = convert_json_to_srt('bad/file.json', 24.0)
    
    assert result == ""
    captured = capsys.readouterr()
    assert "Error reading or parsing JSON file" in captured.out

if __name__ == "__main__":
    pytest.main()