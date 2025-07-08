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
    integration.tc_utils.timecode_from_frame.side_effect = ["00:00:04:04", "00:00:08:08"]
    
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

def test_export_and_reimport_subtitles_no_timeline(mock_resolve_api):
    """Test re-import process when timeline is not available."""
    mock_resolve_api["project"].GetCurrentTimeline.return_value = None
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.export_and_reimport_subtitles(1)
        assert result is False
        mock_print.assert_called_with("ERROR: No active timeline, project, or timecode utility.")

def test_export_and_reimport_subtitles_no_media_pool(mock_resolve_api):
    """Test re-import process when media pool is not available."""
    mock_resolve_api["project"].GetMediaPool.return_value = None
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.export_and_reimport_subtitles(1)
        assert result is False
        mock_print.assert_called_with("ERROR: Could not get Media Pool.")

def test_export_and_reimport_subtitles_no_original_subs(mock_resolve_api):
    """Test re-import process when there are no subtitles to export."""
    integration = ResolveIntegration()
    integration.get_subtitles_with_timecode = MagicMock(return_value=[])
    with patch('builtins.print') as mock_print:
        result = integration.export_and_reimport_subtitles(1)
        assert result is False
        mock_print.assert_called_with("INFO: No subtitles to export.")

def test_export_and_reimport_subtitles_import_fails(mock_resolve_api, mocker):
    """Test re-import process when SRT import fails."""
    mocker.patch('builtins.open', mock_open(read_data="srt content"))
    mocker.patch('src.resolve_integration.tempfile.TemporaryDirectory')
    
    integration = ResolveIntegration()
    integration.get_subtitles_with_timecode = MagicMock(return_value=[{'id': 1, 'in_frame': 10, 'out_frame': 20, 'text': 'test'}])
    mock_resolve_api["project"].GetMediaPool().ImportMedia.return_value = [] # Simulate import failure
    
    with patch('builtins.print') as mock_print:
        result = integration.export_and_reimport_subtitles(1)
        assert result is False
        mock_print.assert_any_call("ERROR: Failed to import SRT file.")

def test_export_and_reimport_subtitles_append_fails(mock_resolve_api, mocker):
    """Test re-import process when appending to timeline fails."""
    mocker.patch('builtins.open', mock_open(read_data="srt content"))
    mocker.patch('src.resolve_integration.tempfile.TemporaryDirectory')
    
    mock_pool_item = MagicMock()
    mock_resolve_api["project"].GetMediaPool().ImportMedia.return_value = [mock_pool_item]
    mock_resolve_api["project"].GetMediaPool().AppendToTimeline.return_value = False # Simulate append failure
    mock_resolve_api["timeline"].GetTrackCount.return_value = 2 # After AddTrack

    integration = ResolveIntegration()
    integration.get_subtitles_with_timecode = MagicMock(return_value=[{'id': 1, 'in_frame': 0, 'out_frame': 10, 'text': 'test'}])
    
    with patch('builtins.print') as mock_print:
        result = integration.export_and_reimport_subtitles(1)
        assert result is False
        mock_print.assert_any_call("ERROR: Failed to append clip to the timeline.")
        # Check if tracks are re-enabled on failure
        mock_resolve_api["timeline"].SetTrackEnable.assert_any_call("subtitle", 2, True)

def test_export_and_reimport_subtitles_fatal_exception(mock_resolve_api, mocker):
    """Test re-import process with an unexpected fatal exception."""
    mocker.patch('src.resolve_integration.tempfile.TemporaryDirectory', side_effect=Exception("Disk is full"))
    integration = ResolveIntegration()
    with patch('builtins.print') as mock_print:
        result = integration.export_and_reimport_subtitles(1)
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
