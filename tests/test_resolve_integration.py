# tests/test_resolve_integration.py
import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.resolve_integration import ResolveIntegration

@pytest.fixture
def mock_resolve_api(mocker):
    """Fixture to mock the DaVinci Resolve API."""
    mock_resolve = MagicMock()
    mock_project_manager = MagicMock()
    mock_project = MagicMock()
    mock_timeline = MagicMock()

    mock_resolve.GetProjectManager.return_value = mock_project_manager
    mock_project_manager.GetCurrentProject.return_value = mock_project
    mock_project.GetCurrentTimeline.return_value = mock_timeline

    mocker.patch('src.resolve_integration.ResolveIntegration._get_resolve_instance', return_value=mock_resolve)
    mocker.patch('src.resolve_integration.TimecodeUtils', return_value=MagicMock())
    
    return {
        "resolve": mock_resolve,
        "project_manager": mock_project_manager,
        "project": mock_project,
        "timeline": mock_timeline,
    }

def test_resolve_integration_init_success(mock_resolve_api):
    """Test successful initialization of ResolveIntegration."""
    integration = ResolveIntegration()
    assert integration.resolve is not None
    assert integration.project_manager is not None
    assert integration.project is not None
    assert integration.timeline is not None

def test_resolve_integration_init_no_resolve(mocker):
    """Test initialization when connection to Resolve fails."""
    mocker.patch('src.resolve_integration.ResolveIntegration._get_resolve_instance', return_value=None)
    with pytest.raises(ImportError):
        ResolveIntegration()

def test_get_current_timeline_info_success(mock_resolve_api):
    """Test get_current_timeline_info with a valid timeline."""
    mock_resolve_api["timeline"].GetSetting.return_value = 24.0
    mock_resolve_api["timeline"].GetTrackCount.return_value = 2
    integration = ResolveIntegration()
    info = integration.get_current_timeline_info()
    assert info['frame_rate'] == 24.0
    assert info['track_count'] == 2

def test_get_current_timeline_info_no_timeline(mock_resolve_api):
    """Test get_current_timeline_info when there is no timeline."""
    mock_resolve_api["project"].GetCurrentTimeline.return_value = None
    integration = ResolveIntegration()
    assert integration.get_current_timeline_info() is None

def test_get_subtitles_success(mock_resolve_api):
    """Test get_subtitles with a valid track."""
    mock_sub = MagicMock()
    mock_resolve_api["timeline"].GetItemListInTrack.return_value = [mock_sub]
    integration = ResolveIntegration()
    subs = integration.get_subtitles(1)
    assert len(subs) == 1
    assert subs[0] == mock_sub

def test_get_subtitles_no_timeline(mock_resolve_api):
    """Test get_subtitles when there is no timeline."""
    mock_resolve_api["project"].GetCurrentTimeline.return_value = None
    integration = ResolveIntegration()
    assert integration.get_subtitles(1) == []

def test_get_subtitles_with_timecode_success(mock_resolve_api):
    """Test get_subtitles_with_timecode."""
    mock_sub = MagicMock()
    mock_sub.GetStart.return_value = 100
    mock_sub.GetEnd.return_value = 200
    mock_sub.GetName.return_value = "Test Sub"
    mock_resolve_api["timeline"].GetItemListInTrack.return_value = [mock_sub]
    mock_resolve_api["timeline"].GetSetting.side_effect = [24.0, '0'] # frame_rate, drop_frame
    
    integration = ResolveIntegration()
    integration.tc_utils.timecode_from_frame_to_ms_format.side_effect = ["00:00:04:04", "00:00:08:08"]
    
    subs = integration.get_subtitles_with_timecode(1)
    assert len(subs) == 1
    assert subs[0]['text'] == "Test Sub"
    assert subs[0]['in_timecode'] == "00:00:04:04"
    assert subs[0]['out_timecode'] == "00:00:08:08"

def test_set_active_subtitle_track_success(mock_resolve_api):
    """Test set_active_subtitle_track."""
    mock_resolve_api["timeline"].GetTrackCount.return_value = 2
    integration = ResolveIntegration()
    result = integration.set_active_subtitle_track(1)
    assert result is True
    mock_resolve_api["timeline"].SetTrackEnable.assert_any_call("subtitle", 1, True)
    mock_resolve_api["timeline"].SetTrackEnable.assert_any_call("subtitle", 2, False)

def test_set_active_subtitle_track_index_out_of_bounds(mock_resolve_api):
    """Test set_active_subtitle_track with an out-of-bounds index."""
    mock_resolve_api["timeline"].GetTrackCount.return_value = 2
    integration = ResolveIntegration()
    result = integration.set_active_subtitle_track(3) # Index 3 is out of bounds for 2 tracks
    assert result is False
    mock_resolve_api["timeline"].SetTrackEnable.assert_not_called()

def test_export_subtitles_to_json_success(mock_resolve_api, mocker):
    """Test export_subtitles_to_json."""
    mocker.patch('src.resolve_integration.tempfile.gettempdir', return_value="/tmp")
    mocker.patch('src.resolve_integration.os.path.join', return_value="/tmp/subs.json")
    mocker.patch('builtins.open', mock_open())
    mocker.patch('src.resolve_integration.json.dump')

    integration = ResolveIntegration()
    # Mock the get_subtitles_with_timecode to return some data
    integration.get_subtitles_with_timecode = MagicMock(return_value=[
        {'id': 1, 'in_timecode': '00:01', 'out_timecode': '00:02', 'text': 'Hello'}
    ])
    
    path = integration.export_subtitles_to_json(1)
    assert path == "/tmp/subs.json"

def test_export_subtitles_to_json_no_subs(mock_resolve_api):
    """Test export_subtitles_to_json when there are no subtitles."""
    integration = ResolveIntegration()
    integration.get_subtitles_with_timecode = MagicMock(return_value=[])
    assert integration.export_subtitles_to_json(1) is None

def test_export_subtitles_to_json_exception(mock_resolve_api, mocker):
    """Test export_subtitles_to_json with an exception."""
    mocker.patch('src.resolve_integration.json.dump', side_effect=Exception("Test Error"))
    integration = ResolveIntegration()
    integration.get_subtitles_with_timecode = MagicMock(return_value=[
        {'id': 1, 'in_timecode': '00:01', 'out_timecode': '00:02', 'text': 'Hello'}
    ])
    with patch('builtins.print') as mock_print:
        path = integration.export_subtitles_to_json(1)
        assert path is None
        mock_print.assert_called_once()


def test_export_subtitles_to_srt_no_timeline(mock_resolve_api):
    """Test export_subtitles_to_srt when there is no timeline."""
    mock_resolve_api["project"].GetCurrentTimeline.return_value = None
    integration = ResolveIntegration()
    assert integration.export_subtitles_to_srt(1) is None

def test_export_subtitles_to_srt_no_subtitles(mock_resolve_api):
    """Test export_subtitles_to_srt when there are no subtitles."""
    integration = ResolveIntegration()
    integration.get_subtitles_with_timecode = MagicMock(return_value=[])
    result = integration.export_subtitles_to_srt(1)
    assert result == ""

def test_export_subtitles_to_srt_with_data(mock_resolve_api):
    """Test successful export of subtitles to SRT format."""
    integration = ResolveIntegration()

    # Mock the data returned by get_subtitles_with_timecode
    mock_subs_data = [
        {'id': 1, 'in_frame': 24, 'out_frame': 72, 'text': 'Hello world.'},
        {'id': 2, 'in_frame': 96, 'out_frame': 144, 'text': 'This is a test.'}
    ]
    integration.get_subtitles_with_timecode = MagicMock(return_value=mock_subs_data)

    # Mock timeline settings
    mock_resolve_api["timeline"].GetSetting.return_value = 24.0

    # Mock timecode conversion
    # Mock timecode conversion
    def mock_timecode_to_srt(frame, rate):
        total_seconds = frame / rate
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds * 1000) % 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    integration.tc_utils.timecode_to_srt_format.side_effect = mock_timecode_to_srt
    mock_resolve_api["timeline"].GetStartTimecode.return_value = "00:00:00:00"
    mock_resolve_api["timeline"].GetStartFrame.return_value = 0


    expected_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:03,000\n"
        "Hello world.\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:06,000\n"
        "This is a test.\n\n"
    )
 
    result = integration.export_subtitles_to_srt(1)
    assert result.strip() == expected_srt.strip()
 
    # Verify that timecode conversion was called correctly
    integration.tc_utils.timecode_to_srt_format.assert_any_call(24, 24.0)
    integration.tc_utils.timecode_to_srt_format.assert_any_call(72, 24.0)
    integration.tc_utils.timecode_to_srt_format.assert_any_call(96, 24.0)
    integration.tc_utils.timecode_to_srt_format.assert_any_call(144, 24.0)

@pytest.mark.parametrize(
    "start_timecode, zero_based, expected_srt_output",
    [
        # Scenario 1: Standard timeline (starts at 00:00:00:00), not zero-based
        (
            "00:00:00:00",
            False,
            "1\n00:00:05,000 --> 00:00:10,000\nSubtitle 1\n\n"
            "2\n00:00:15,000 --> 00:00:20,000\nSubtitle 2\n\n"
        ),
        # Scenario 2: Standard timeline, zero-based (should be the same as not zero-based)
        (
            "00:00:00:00",
            True,
            "1\n00:00:05,000 --> 00:00:10,000\nSubtitle 1\n\n"
            "2\n00:00:15,000 --> 00:00:20,000\nSubtitle 2\n\n"
        ),
        # Scenario 3: Timeline starts at 01:00:00:00, not zero-based (output should be offset)
        (
            "01:00:00:00",
            False,
            "1\n01:00:05,000 --> 01:00:10,000\nSubtitle 1\n\n"
            "2\n01:00:15,000 --> 01:00:20,000\nSubtitle 2\n\n"
        ),
        # Scenario 4: Timeline starts at 01:00:00:00, but zero-based (output should be like a standard timeline)
        (
            "01:00:00:00",
            True,
            "1\n00:00:05,000 --> 00:00:10,000\nSubtitle 1\n\n"
            "2\n00:00:15,000 --> 00:00:20,000\nSubtitle 2\n\n"
        ),
    ]
)
def test_export_subtitles_to_srt_scenarios(mock_resolve_api, start_timecode, zero_based, expected_srt_output):
    """
    Test export_subtitles_to_srt with different timeline start times and zero_based flag.
    """
    integration = ResolveIntegration()
    frame_rate = 24.0
    hour_in_frames = int(frame_rate * 3600)

    # Mock timeline settings based on scenario
    mock_resolve_api["timeline"].GetSetting.return_value = frame_rate
    mock_resolve_api["timeline"].GetStartTimecode.return_value = start_timecode
    
    # Define subtitle data with absolute frame numbers
    # If the timeline starts at 1 hour, the frames will be large
    start_frame_offset = hour_in_frames if start_timecode.startswith("01:") else 0
    mock_subs_data = [
        {'id': 1, 'in_frame': 120 + start_frame_offset, 'out_frame': 240 + start_frame_offset, 'text': 'Subtitle 1'},
        {'id': 2, 'in_frame': 360 + start_frame_offset, 'out_frame': 480 + start_frame_offset, 'text': 'Subtitle 2'}
    ]
    integration.get_subtitles_with_timecode = MagicMock(return_value=mock_subs_data)
    
    # `GetStartFrame` should always return the timeline's absolute start frame.
    mock_resolve_api["timeline"].GetStartFrame.return_value = start_frame_offset

    # Mock the final timecode conversion to SRT format
    def mock_timecode_to_srt(frame, rate):
        total_seconds = frame / rate
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds * 1000) % 1000)
        
        # In the non-zero-based 1-hour start scenario, the frame number passed to this function
        # will already have the 1-hour offset included from the main function's logic.
        if not zero_based and start_timecode.startswith("01:"):
            # We need to add the hour back for the final timecode string.
            hours += 1
            
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    integration.tc_utils.timecode_to_srt_format = MagicMock(side_effect=mock_timecode_to_srt)

    # Execute the function
    result = integration.export_subtitles_to_srt(track_number=1, zero_based=zero_based)

    # Assert the output is correct
    # A direct string comparison can be brittle, let's compare line by line after splitting.
    assert result.strip() == expected_srt_output.strip()


def test_resolve_integration_init_timecode_utils_fails(mock_resolve_api, mocker):
    """Test initialization when TimecodeUtils fails to initialize."""
    mocker.patch('src.resolve_integration.TimecodeUtils', side_effect=Exception("TC Init Error"))
    mock_print = mocker.patch('builtins.print')
    
    integration = ResolveIntegration()
    
    assert integration.tc_utils is None
    mock_print.assert_called_with("Error initializing TimecodeUtils: TC Init Error")

def test_get_subtitles_with_timecode_no_tc_utils(mock_resolve_api):
    """Test get_subtitles_with_timecode when TimecodeUtils is not available."""
    mock_sub = MagicMock()
    mock_resolve_api["timeline"].GetItemListInTrack.return_value = [mock_sub]
    
    integration = ResolveIntegration()
    integration.tc_utils = None  # Simulate TC utils failing
    
    with patch('builtins.print') as mock_print:
        subs = integration.get_subtitles_with_timecode(1)
        assert subs == []
        mock_print.assert_called_with("TimecodeUtils not available.")

def test_reimport_from_json_no_timeline(mock_resolve_api):
    """Test re-import process when timeline is not available."""
    mock_resolve_api["project"].GetCurrentTimeline.return_value = None
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.reimport_from_json_file("dummy.json")
        assert result is False
        mock_print.assert_called_with("ERROR: No active timeline, project, or timecode utility.")

def test_reimport_from_json_no_media_pool(mock_resolve_api):
    """Test re-import process when media pool is not available."""
    mock_resolve_api["project"].GetMediaPool.return_value = None
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.reimport_from_json_file("dummy.json")
        assert result is False
        mock_print.assert_called_with("ERROR: Could not get Media Pool.")

def test_reimport_from_json_no_subs(mock_resolve_api, temp_json_file):
    """Test re-import process when there are no subtitles to import."""
    json_path = temp_json_file([])
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.reimport_from_json_file(json_path)
        assert result is False
        mock_print.assert_called_with("INFO: No subtitles to import from JSON.")

def test_reimport_from_json_import_fails(mock_resolve_api, temp_json_file, mocker):
    """Test re-import process when SRT import fails."""
    json_path = temp_json_file([{'start': '00:00:01,000', 'end': '00:00:02,000', 'text': 'test'}])
    
    mocker.patch('src.resolve_integration.convert_json_to_srt', return_value="dummy srt content")
    
    integration = ResolveIntegration()
    mock_resolve_api["project"].GetMediaPool().ImportMedia.return_value = [] # Simulate import failure
    
    with patch('builtins.print') as mock_print:
        result = integration.reimport_from_json_file(json_path)
        assert result is False
        mock_print.assert_any_call("ERROR: Failed to import SRT file.")

def test_reimport_from_json_append_fails(mock_resolve_api, temp_json_file, mocker):
    """Test re-import process when appending to timeline fails."""
    json_path = temp_json_file([{'start': '00:00:01,000', 'end': '00:00:02,000', 'text': 'test'}])
    
    mocker.patch('src.resolve_integration.convert_json_to_srt', return_value="dummy srt content")
    mocker.patch('src.resolve_integration.timecode_to_frames', return_value=10)

    mock_pool_item = MagicMock()
    mock_resolve_api["project"].GetMediaPool().ImportMedia.return_value = [mock_pool_item]
    mock_resolve_api["project"].GetMediaPool().AppendToTimeline.return_value = False # Simulate append failure
    mock_resolve_api["timeline"].GetTrackCount.return_value = 2 # After AddTrack

    integration = ResolveIntegration()
    
    with patch('builtins.print') as mock_print:
        result = integration.reimport_from_json_file(json_path)
        assert result is False
        mock_print.assert_any_call("ERROR: Failed to append clip to the timeline.")
        # Check if tracks are re-enabled on failure
        mock_resolve_api["timeline"].SetTrackEnable.assert_any_call("subtitle", 2, True)

def test_reimport_from_json_fatal_exception(mock_resolve_api, mocker):
    """Test re-import process with an unexpected fatal exception."""
    mocker.patch('builtins.open', side_effect=Exception("Disk is full"))
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.reimport_from_json_file("dummy.json")
        assert result is False
        mock_print.assert_any_call("FATAL: An unexpected exception occurred: Disk is full")

def test_get_resolve_instance_fusionscript_not_found(mocker):
    """Test _get_resolve_instance when fusionscript is not found."""
    mocker.patch.dict('sys.modules', {'fusionscript': None})
    with pytest.raises(ImportError):
        ResolveIntegration()

def test_get_resolve_instance_bmd_python_not_found(mocker):
    """Test _get_resolve_instance when DaVinciResolveScript is not found."""
    mocker.patch.dict('sys.modules', {'DaVinciResolveScript': None})
    with pytest.raises(ImportError):
        ResolveIntegration()

def test_update_subtitle_text_success(mock_resolve_api):
    """Test successful update of subtitle text."""
    integration = ResolveIntegration()
    mock_item = MagicMock()
    mock_item.GetStart.return_value = 12345
    mock_item.UpdateText.return_value = True
    mock_resolve_api["timeline"].GetItemListInTrack.return_value = [mock_item]

    subtitle_obj = {'id': 1, 'track_index': 1, 'in_frame': 12345}
    new_text = "Updated text"

    result = integration.update_subtitle_text(subtitle_obj, new_text)

    assert result is True
    mock_item.SetClipColor.assert_called_with('Orange')
    mock_item.UpdateText.assert_called_once_with(new_text)

def test_update_subtitle_text_no_timeline(mock_resolve_api):
    """Test update_subtitle_text when there is no timeline."""
    mock_resolve_api["project"].GetCurrentTimeline.return_value = None
    integration = ResolveIntegration()
    result = integration.update_subtitle_text({'id': 1}, "text")
    assert result is False

def test_update_subtitle_text_item_not_found(mock_resolve_api):
    """Test update_subtitle_text when the item is not found in the timeline."""
    integration = ResolveIntegration()
    mock_resolve_api["timeline"].GetItemListInTrack.return_value = []

    result = integration.update_subtitle_text({'id': 1, 'track_index': 1, 'in_frame': 123}, "text")

    assert result is False


import json
import os
from src.resolve_integration import convert_json_to_srt, timecode_to_frames

# Fixture to create a temporary JSON file for testing
@pytest.fixture
def temp_json_file(tmpdir):
    def _create_file(data):
        file_path = tmpdir.join("test_subtitles.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(file_path)
    return _create_file

def test_timecode_to_frames_valid_srt():
    """Test valid HH:MM:SS,ms format."""
    assert timecode_to_frames("00:00:01,500", 24.0) == 36
    assert timecode_to_frames("01:00:00,000", 24.0) == 86400
    assert timecode_to_frames("00:01:30,500", 30.0) == 2715

@pytest.mark.parametrize("invalid_tc, expected_error_msg", [
    ("00:00:01:500", "Invalid timecode format. Expected HH:MM:SS,ms."),
    ("00:01,500", "Invalid timecode format. Expected HH:MM:SS,ms."),
    ("aa:bb:cc,dd", "Invalid timecode format. Components must be integers.")
])
def test_timecode_to_frames_invalid_srt(invalid_tc, expected_error_msg):
    """Test invalid HH:MM:SS,ms formats."""
    with pytest.raises(ValueError, match=expected_error_msg):
        timecode_to_frames(invalid_tc, 24.0)

def test_convert_json_to_srt_success(temp_json_file):
    """Test successful conversion from a valid JSON file to SRT format."""
    subtitle_data = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:03,500", "text": "First line."},
        {"index": 2, "start": "00:00:04,000", "end": "00:00:06,000", "text": "Second line."}
    ]
    json_path = temp_json_file(subtitle_data)
    frame_rate = 24.0
    
    expected_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:03,500\n"
        "First line.\n\n"
        "2\n"
        "00:00:04,000 --> 00:00:06,000\n"
        "Second line."
    )
    
    result = convert_json_to_srt(json_path, frame_rate)
    # rstrip to remove trailing newline from the expected result for comparison
    assert result.strip() == expected_srt.strip()

def test_convert_json_to_srt_file_not_found(capsys):
    """Test conversion when the JSON file does not exist."""
    result = convert_json_to_srt("non_existent_file.json", 24.0)
    assert result == ""
    captured = capsys.readouterr()
    assert "Error reading or parsing JSON file" in captured.out

def test_convert_json_to_srt_empty_file(temp_json_file, capsys):
    """Test conversion with an empty JSON file."""
    json_path = temp_json_file([])
    result = convert_json_to_srt(json_path, 24.0)
    assert result == ""
    # No error should be printed for an empty list
    captured = capsys.readouterr()
    assert captured.out == ""

def test_convert_json_to_srt_malformed_json(tmpdir, capsys):
    """Test conversion with a malformed JSON file."""
    file_path = tmpdir.join("malformed.json")
    with open(file_path, 'w') as f:
        f.write("{'bad': 'json',}") # Invalid JSON
    
    result = convert_json_to_srt(str(file_path), 24.0)
    assert result == ""
    captured = capsys.readouterr()
    assert "Error reading or parsing JSON file" in captured.out

def test_convert_json_to_srt_missing_keys(temp_json_file, capsys):
    """Test conversion with a JSON entry missing required keys."""
    # Entry at index 1 is missing the 'end' key
    subtitle_data = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:03,000", "text": "Good one."},
        {"index": 2, "start": "00:00:04,000", "text": "Bad one."}
    ]
    json_path = temp_json_file(subtitle_data)
    
    result = convert_json_to_srt(json_path, 24.0)
    
    # Only the valid entry should be in the output
    expected_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:03,000\n"
        "Good one."
    )
    
    assert result.strip() == expected_srt.strip()
    captured = capsys.readouterr()
    assert "Skipping invalid subtitle entry at index 1" in captured.out

def test_convert_json_to_srt_invalid_timecode(temp_json_file, capsys):
    """Test conversion with an invalid timecode format in the JSON."""
    subtitle_data = [
        {"index": 1, "start": "00:00:01,000", "end": "00:00:03,000", "text": "Valid"},
        {"index": 2, "start": "invalid-timecode", "end": "00:00:06,000", "text": "Invalid"}
    ]
    json_path = temp_json_file(subtitle_data)
    
    result = convert_json_to_srt(json_path, 24.0)
    
    expected_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:03,000\n"
        "Valid"
    )

    assert result.strip() == expected_srt.strip()
    captured = capsys.readouterr()
    assert "Skipping invalid subtitle entry at index 1" in captured.out


def test_reimport_from_json_with_one_hour_offset(mock_resolve_api, temp_json_file, mocker):
    """
    Test re-importing subtitles on a timeline that starts at 01:00:00:00.
    This test ensures that the timecode is not double-offset.
    """
    # 1. Arrange
    frame_rate = 24.0
    one_hour_in_frames = int(3600 * frame_rate)
    
    # Mock timeline settings to simulate a 1-hour start time
    mock_timeline = mock_resolve_api["timeline"]
    mock_timeline.GetSetting.return_value = frame_rate
    mock_timeline.GetStartFrame.return_value = one_hour_in_frames
    mock_timeline.GetStartTimecode.return_value = "01:00:00:00"

    # Mock Media Pool and other necessary components
    mock_media_pool = mock_resolve_api["project"].GetMediaPool()
    mock_pool_item = MagicMock()
    mock_media_pool.ImportMedia.return_value = [mock_pool_item]
    mock_media_pool.AppendToTimeline.return_value = True

    # Mock TimecodeUtils methods
    integration = ResolveIntegration()
    # Ensure tc_utils is mocked properly
    if not hasattr(integration, 'tc_utils') or integration.tc_utils is None:
        integration.tc_utils = MagicMock()

    # This is the absolute frame number we expect for a 1-hour 10-second timecode
    expected_absolute_frame = one_hour_in_frames + int(10 * frame_rate)
    
    def mock_tc_from_frame(frame, rate, drop_frame):
        # This function should convert an absolute frame number to a timecode string
        total_seconds = frame / rate
        h = int(total_seconds / 3600)
        m = int((total_seconds % 3600) / 60)
        s = int(total_seconds % 60)
        f = int(frame % rate)
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    integration.tc_utils.timecode_from_frame.side_effect = mock_tc_from_frame
    
    # Create a JSON file with a subtitle starting at 1 hour and 10 seconds
    json_data = [{
        "index": 1,
        "start": "01:00:10,000",
        "end": "01:00:12,000",
        "text": "Test subtitle with offset"
    }]
    json_path = temp_json_file(json_data)

    # 2. Act
    result = integration.reimport_from_json_file(json_path)

    # 3. Assert
    assert result is True, "Re-import should succeed"
    
    # Verify that the playhead is set to the correct, non-offset timecode
    # The `timecode_to_frames` in the SUT will calculate the absolute frame number
    # and `timecode_from_frame` will convert it back to the correct TC string.
    # We expect the final timecode to match the original start time from the JSON.
    mock_timeline.SetCurrentTimecode.assert_called_once()
    called_timecode = mock_timeline.SetCurrentTimecode.call_args[0][0]
    
    # The expected timecode should be exactly what was in the JSON file.
    # The mock for timecode_from_frame will produce HH:MM:SS:FF format.
    expected_timecode_str = "01:00:10:00"
    assert called_timecode == expected_timecode_str

    # Verify that the SRT clip was created and appended correctly
    mock_media_pool.ImportMedia.assert_called_once()
    mock_media_pool.AppendToTimeline.assert_called_once_with(mock_pool_item)
    
    # Verify a new track was created and isolated
    mock_timeline.AddTrack.assert_called_with("subtitle")
    
