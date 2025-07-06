import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# The pytest.ini configuration handles the python path.
# No need to manually modify sys.path here.

from src.resolve_integration import ResolveIntegration

@pytest.fixture
def mock_timeline():
    """Fixture to create a mock timeline object."""
    timeline = MagicMock()
    timeline.GetTrackCount.return_value = 3
    return timeline

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_set_active_subtitle_track_valid_index(mock_get_resolve, mock_timeline):
    """
    Test that the target track is enabled and all other tracks are disabled
    when a valid track index is provided.
    """
    mock_get_resolve.return_value = MagicMock()
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline

    result = integration.set_active_subtitle_track(2)

    assert result is True
    mock_timeline.GetTrackCount.assert_called_once_with("subtitle")
    
    # Verify that SetTrackEnable was called correctly for all tracks
    expected_calls = [
        (( "subtitle", 1, False),),
        (( "subtitle", 2, True),),
        (( "subtitle", 3, False),)
    ]
    
    # Check if the calls were made, regardless of order
    assert mock_timeline.SetTrackEnable.call_count == 3
    for call_args in expected_calls:
        mock_timeline.SetTrackEnable.assert_any_call(*call_args[0])


@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_set_active_subtitle_track_invalid_index_too_low(mock_get_resolve, mock_timeline):
    """
    Test that the function returns False for a track index less than 1.
    """
    mock_get_resolve.return_value = MagicMock()
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline

    result = integration.set_active_subtitle_track(0)

    assert result is False
    mock_timeline.SetTrackEnable.assert_not_called()

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_set_active_subtitle_track_invalid_index_too_high(mock_get_resolve, mock_timeline):
    """
    Test that the function returns False for a track index greater than the track count.
    """
    mock_get_resolve.return_value = MagicMock()
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline

    result = integration.set_active_subtitle_track(4)

    assert result is False
    mock_timeline.SetTrackEnable.assert_not_called()

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_set_active_subtitle_track_no_timeline(mock_get_resolve):
    """
    Test that the function returns False when the timeline object does not exist.
    """
    mock_get_resolve.return_value = MagicMock()
    
    integration = ResolveIntegration()
    integration.timeline = None # Simulate no timeline

    result = integration.set_active_subtitle_track(1)

    assert result is False


@patch('builtins.__import__')
def test_init_success(mock_import):
    """Test successful initialization of ResolveIntegration."""
    mock_resolve = MagicMock()
    mock_fusionscript = MagicMock()
    mock_fusionscript.scriptapp.return_value = mock_resolve
    
    # Configure the mock to return fusionscript on the first import
    mock_import.side_effect = lambda name, *args, **kwargs: {'fusionscript': mock_fusionscript}[name]

    integration = ResolveIntegration()
    
    assert integration.resolve is not None
    mock_fusionscript.scriptapp.assert_called_once_with("Resolve")
    assert integration.project_manager is not None
    assert integration.project is not None
    assert integration.timeline is not None

@patch('builtins.__import__', side_effect=ImportError)
def test_init_import_error(mock_import):
    """Test that ImportError is raised if Resolve cannot be connected."""
    with pytest.raises(ImportError, match="Could not connect to DaVinci Resolve"):
        ResolveIntegration()

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_current_timeline_info_success(mock_get_resolve):
    """Test getting timeline info successfully."""
    mock_get_resolve.return_value = MagicMock()
    integration = ResolveIntegration()
    
    mock_timeline = MagicMock()
    mock_timeline.GetSetting.return_value = 24.0
    mock_timeline.GetTrackCount.return_value = 2
    integration.timeline = mock_timeline
    
    info = integration.get_current_timeline_info()
    
    assert info == {'frame_rate': 24.0, 'track_count': 2}
    mock_timeline.GetSetting.assert_called_once_with('timelineFrameRate')
    mock_timeline.GetTrackCount.assert_called_once_with('subtitle')

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_current_timeline_info_no_timeline(mock_get_resolve):
    """Test getting timeline info when no timeline exists."""
    mock_get_resolve.return_value = MagicMock()
    integration = ResolveIntegration()
    integration.timeline = None
    
    info = integration.get_current_timeline_info()
    
    assert info is None

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_subtitles_success(mock_get_resolve):
    """Test getting subtitles successfully."""
    mock_get_resolve.return_value = MagicMock()
    integration = ResolveIntegration()

    mock_timeline = MagicMock()
    mock_subtitles = [MagicMock(), MagicMock()]
    mock_timeline.GetItemListInTrack.return_value = mock_subtitles
    integration.timeline = mock_timeline

    subtitles = integration.get_subtitles(track_number=1)

    assert subtitles == mock_subtitles
    mock_timeline.GetItemListInTrack.assert_called_once_with('subtitle', 1)

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_subtitles_no_timeline(mock_get_resolve):
    """Test getting subtitles when no timeline exists."""
    mock_get_resolve.return_value = MagicMock()
    integration = ResolveIntegration()
    integration.timeline = None

    subtitles = integration.get_subtitles()

    assert subtitles == []


@pytest.fixture
def mock_sub_obj():
    """Fixture to create a mock subtitle object."""
    sub_obj = MagicMock()
    sub_obj.GetStart.return_value = 0
    sub_obj.GetEnd.return_value = 24
    sub_obj.GetName.return_value = "Test Subtitle"
    return sub_obj

@patch('src.resolve_integration.TimecodeUtils')
@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_subtitles_with_timecode_success(mock_get_resolve, mock_timecode_utils, mock_timeline, mock_sub_obj):
    """Test getting subtitles with timecode successfully."""
    mock_get_resolve.return_value = MagicMock()
    
    # Mock timeline settings
    mock_timeline.GetSetting.side_effect = lambda key: 24.0 if key == 'timelineFrameRate' else '0'
    mock_timeline.GetItemListInTrack.return_value = [mock_sub_obj]
    
    # Mock TimecodeUtils
    mock_tc_instance = mock_timecode_utils.return_value
    mock_tc_instance.timecode_from_frame.side_effect = ["00:00:00:00", "00:00:01:00"]
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline
    
    subtitles = integration.get_subtitles_with_timecode()
    
    assert len(subtitles) == 1
    sub = subtitles[0]
    assert sub['id'] == 1
    assert sub['text'] == "Test Subtitle"
    assert sub['in_frame'] == 0
    assert sub['out_frame'] == 24
    assert sub['in_timecode'] == "00:00:00:00"
    assert sub['out_timecode'] == "00:00:01:00"
    
    mock_timeline.GetSetting.assert_any_call('timelineFrameRate')
    mock_timeline.GetSetting.assert_any_call('timelineDropFrame')
    mock_timeline.GetItemListInTrack.assert_called_once_with('subtitle', 1)
    mock_timecode_utils.assert_called_once_with(integration.resolve)
    mock_tc_instance.timecode_from_frame.assert_any_call(0, 24.0, False)
    mock_tc_instance.timecode_from_frame.assert_any_call(24, 24.0, False)

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_subtitles_with_timecode_no_timeline(mock_get_resolve):
    """Test getting subtitles with timecode when no timeline exists."""
    mock_get_resolve.return_value = MagicMock()
    integration = ResolveIntegration()
    integration.timeline = None
    
    subtitles = integration.get_subtitles_with_timecode()
    
    assert subtitles == []

@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_subtitles_with_timecode_no_subtitles(mock_get_resolve, mock_timeline):
    """Test getting subtitles with timecode when there are no subtitles."""
    mock_get_resolve.return_value = MagicMock()
    mock_timeline.GetItemListInTrack.return_value = []
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline
    
    subtitles = integration.get_subtitles_with_timecode()
    
    assert subtitles == []
    mock_timeline.GetItemListInTrack.assert_called_once_with('subtitle', 1)

@patch('src.resolve_integration.TimecodeUtils', side_effect=Exception("TC Init Error"))
@patch('src.resolve_integration.ResolveIntegration._get_resolve_instance')
def test_get_subtitles_with_timecode_tc_utils_error(mock_get_resolve, mock_timecode_utils, mock_timeline, mock_sub_obj):
    """Test handling of TimecodeUtils initialization error."""
    mock_get_resolve.return_value = MagicMock()
    mock_timeline.GetSetting.side_effect = lambda key: 24.0 if key == 'timelineFrameRate' else '0'
    mock_timeline.GetItemListInTrack.return_value = [mock_sub_obj]
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline
    
    subtitles = integration.get_subtitles_with_timecode()
    
    assert subtitles == []
    mock_timecode_utils.assert_called_once()
