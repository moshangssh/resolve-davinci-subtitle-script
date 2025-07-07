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
    integration.tc_utils.timecode_from_frame.side_effect = [
        "00:00:01;00",  # Start time for sub 1
        "00:00:03;00",  # End time for sub 1
        "00:00:04;00",  # Start time for sub 2
        "00:00:06;00"   # End time for sub 2
    ]

    expected_srt = (
        "1\n"
        "00,00,01,00 --> 00,00,03,00\n"
        "Hello world.\n\n"
        "2\n"
        "00,00,04,00 --> 00,00,06,00\n"
        "This is a test.\n\n"
    )

    result = integration.export_subtitles_to_srt(1)
    assert result == expected_srt

    # Verify that timecode conversion was called correctly
    integration.tc_utils.timecode_from_frame.assert_any_call(24, 24.0)
    integration.tc_utils.timecode_from_frame.assert_any_call(72, 24.0)
    integration.tc_utils.timecode_from_frame.assert_any_call(96, 24.0)
    integration.tc_utils.timecode_from_frame.assert_any_call(144, 24.0)
