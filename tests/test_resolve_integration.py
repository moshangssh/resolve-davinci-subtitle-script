# tests/test_resolve_integration.py
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

from src.resolve_integration import ResolveIntegration
from src.timecode_utils import TimecodeUtils

# --- Initialization and Connection Tests ---

def test_init_online_with_fusionscript(mocker):
    """Test successful initialization using the fusionscript module."""
    mock_resolve_app = MagicMock()
    mock_fusionscript = MagicMock()
    mock_fusionscript.scriptapp.return_value = mock_resolve_app
    
    mocker.patch.dict(sys.modules, {'fusionscript': mock_fusionscript, 'DaVinciResolveScript': None})
    mocker.patch('src.resolve_integration.TimecodeUtils', side_effect=Exception("TC Init Error"))
    
    integration = ResolveIntegration()
    
    assert integration.initialized is False
    assert integration.resolve == mock_resolve_app
    mock_fusionscript.scriptapp.assert_called_once_with("Resolve")

def test_init_online_with_davinci_resolve_script(mocker):
    """Test successful initialization using the DaVinciResolveScript module."""
    mock_resolve_app = MagicMock()
    mock_dvr_script = MagicMock()
    mock_dvr_script.scriptapp.return_value = mock_resolve_app
    
    mocker.patch.dict(sys.modules, {'fusionscript': None, 'DaVinciResolveScript': mock_dvr_script})
    mocker.patch('src.resolve_integration.TimecodeUtils')
    
    integration = ResolveIntegration()
    
    assert integration.initialized is False
    assert integration.resolve is None
    mock_dvr_script.scriptapp.assert_called_once_with("Resolve")

def test_init_offline_mode(mocker):
    """Test correct initialization when no Resolve API is found."""
    mocker.patch.dict(sys.modules, {'fusionscript': None, 'DaVinciResolveScript': None})
    
    with patch('builtins.print') as mock_print:
        integration = ResolveIntegration()
        assert integration.initialized is False
        mock_print.assert_any_call("LOG: INFO: DaVinci Resolve instance not found. Running in offline mode.")

@pytest.mark.parametrize("error_type, log_message_fragment", [
    (TypeError("Invalid config"), "LOG: ERROR: Error initializing TimecodeUtils due to invalid configuration:"),
    (ValueError("Bad value"), "LOG: ERROR: Error initializing TimecodeUtils due to invalid configuration:"),
    (Exception("Unexpected"), "LOG: CRITICAL: An unexpected error occurred during TimecodeUtils initialization:")
])
def test_init_timecode_utils_fails(mocker, error_type, log_message_fragment):
    """Test that initialization handles errors from TimecodeUtils gracefully."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    mocker.patch('src.resolve_integration.TimecodeUtils', side_effect=error_type)
    
    with patch('builtins.print') as mock_print:
        integration = ResolveIntegration()
        assert integration.initialized is False
        assert integration.tc_utils is None
        
        assert any(log_message_fragment in call.args[0] for call in mock_print.call_args_list)
        mock_print.assert_any_call("LOG: WARNING: TimecodeUtils not available.")

# --- Method Tests ---

def test_get_current_timeline_info_online(mocker):
    """Test get_current_timeline_info in an online state."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    mocker.patch('src.resolve_integration.TimecodeUtils', side_effect=Exception("TC Init Error"))
    
    integration = ResolveIntegration()
    
    assert integration.initialized is False
    integration.timeline = MagicMock()
    integration.timeline.GetSetting.return_value = 24.0
    integration.timeline.GetTrackCount.return_value = 3
    
    info, error = integration.get_current_timeline_info()
    
    assert error is None
    assert info is not None
    assert info['frame_rate'] == 24.0
    assert info['track_count'] == 3

def test_get_subtitles_with_timecode_online(mocker):
    """Test get_subtitles_with_timecode in an online state."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    # CRITICAL: This patch prevents the real TimecodeUtils constructor from running.
    mocker.patch('src.resolve_integration.TimecodeUtils')
    
    # Now that patching is complete, we can instantiate.
    integration = ResolveIntegration()
    assert integration.initialized is True

    # Manually set up mocks on the now-initialized instance
    integration.timeline = MagicMock()
    # The patch above ensures integration.tc_utils is already a MagicMock.
    # We just need to configure it.
    
    mock_sub = MagicMock()
    mock_sub.GetStart.return_value = 100
    mock_sub.GetEnd.return_value = 200
    mock_sub.GetName.return_value = "Test Subtitle"
    
    integration.timeline.GetItemListInTrack.return_value = [mock_sub]
    integration.timeline.GetSetting.return_value = 24.0
    integration.tc_utils.timecode_to_srt_format.side_effect = ["00:00:04,167", "00:00:08,333"]
    
    subs, error = integration.get_subtitles_with_timecode(track_number=1)
    
    assert error is None
    assert len(subs) == 1
    assert subs[0]['text'] == "Test Subtitle"
    assert subs[0]['in_timecode'] == "00:00:04,167"
    assert subs[0]['out_timecode'] == "00:00:08,333"
    assert integration.tc_utils.timecode_to_srt_format.call_count == 2

def test_get_subtitles_with_timecode_no_tc_utils(mocker):
    """Test get_subtitles_with_timecode when tc_utils has failed to initialize."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    mocker.patch('src.resolve_integration.TimecodeUtils', side_effect=Exception("TC Init Error"))

    with patch('builtins.print') as mock_print:
        integration = ResolveIntegration()
        assert integration.initialized is False
        
        integration.timeline = MagicMock()
        integration.timeline.GetSetting.return_value = 24.0
        integration.timeline.GetItemListInTrack.return_value = [MagicMock()]
        
        result, error = integration.get_subtitles_with_timecode(1)
        
        assert result is None, "Result should be None when TimecodeUtils is unavailable"
        assert error is not None, "Error message should be returned"
        assert "TimecodeUtils not available" in error
        
        # Check that a warning was logged
        log_found = any("TimecodeUtils not available" in call.args[0] for call in mock_print.call_args_list)
        assert log_found, "Expected a warning log about TimecodeUtils being unavailable"

def test_export_subtitles_to_srt_calls_formatter(mocker):
    """
    Test that export_subtitles_to_srt correctly calls the centralized format_subtitles_to_srt function.
    """
    # Mock the ResolveIntegration's internal methods
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    mocker.patch('src.resolve_integration.TimecodeUtils')
    
    integration = ResolveIntegration()
    integration.timeline = MagicMock()

    # Mock the return value of get_subtitles_with_timecode
    mock_subtitles = [
        {"in_timecode": "00:00:01,000", "out_timecode": "00:00:02,000", "text": "Test"}
    ]
    mocker.patch.object(integration, 'get_subtitles_with_timecode', return_value=(mock_subtitles, None))
    
    # Mock the timeline settings
    integration.timeline.GetSetting.return_value = '24.0'
    integration.timeline.GetStartTimecode.return_value = '00:00:00:00'
    integration.timeline.GetStartFrame.return_value = 0

    # Mock the centralized formatter function to intercept its call
    mock_format_subtitles = mocker.patch('src.resolve_integration.format_subtitles_to_srt', return_value="--SRT CONTENT--")

    # Execute the method
    result = integration.export_subtitles_to_srt(track_number=1, zero_based=True)

    # --- Assertions ---
    # 1. Check that get_subtitles_with_timecode was called
    integration.get_subtitles_with_timecode.assert_called_once_with(1)

    # 2. Check that the centralized formatter was called with the correct arguments
    expected_subs_for_conversion = [{
        "start": "00:00:01,000",
        "end": "00:00:02,000",
        "text": "Test"
    }]
    mock_format_subtitles.assert_called_once_with(expected_subs_for_conversion, 24.0, 0)

    # 3. Check that the final result is the mocked return value
    assert result == "--SRT CONTENT--"

if __name__ == "__main__":
    pytest.main()
