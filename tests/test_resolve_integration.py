# tests/test_resolve_integration.py
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# This import must be after the path modification
from resolve_integration import ResolveIntegration
from timecode_utils import TimecodeUtils

# --- Initialization and Connection Tests ---

def test_init_online_with_fusionscript(mocker):
    """Test successful initialization using the fusionscript module."""
    mock_resolve_app = MagicMock()
    mock_fusionscript = MagicMock()
    mock_fusionscript.scriptapp.return_value = mock_resolve_app
    
    mocker.patch.dict(sys.modules, {'fusionscript': mock_fusionscript, 'DaVinciResolveScript': None})
    mocker.patch('resolve_integration.TimecodeUtils')
    
    integration = ResolveIntegration()
    
    assert integration.initialized is True
    assert integration.resolve == mock_resolve_app
    mock_fusionscript.scriptapp.assert_called_once_with("Resolve")

def test_init_online_with_davinci_resolve_script(mocker):
    """Test successful initialization using the DaVinciResolveScript module."""
    mock_resolve_app = MagicMock()
    mock_dvr_script = MagicMock()
    mock_dvr_script.scriptapp.return_value = mock_resolve_app
    
    mocker.patch.dict(sys.modules, {'fusionscript': None, 'DaVinciResolveScript': mock_dvr_script})
    mocker.patch('resolve_integration.TimecodeUtils')

    integration = ResolveIntegration()

    assert integration.initialized is True
    assert integration.resolve == mock_resolve_app
    mock_dvr_script.scriptapp.assert_called_once_with("Resolve")

def test_init_offline_mode(mocker):
    """Test correct initialization when no Resolve API is found."""
    mocker.patch.dict(sys.modules, {'fusionscript': None, 'DaVinciResolveScript': None})
    
    with patch('builtins.print') as mock_print:
        integration = ResolveIntegration()
        assert integration.initialized is False
        mock_print.assert_called_once_with("LOG: INFO: DaVinci Resolve instance not found. Running in offline mode.")

@pytest.mark.parametrize("error_type, log_message_fragment", [
    (TypeError("Invalid config"), "LOG: ERROR: Error initializing TimecodeUtils due to invalid configuration:"),
    (ValueError("Bad value"), "LOG: ERROR: Error initializing TimecodeUtils due to invalid configuration:"),
    (Exception("Unexpected"), "LOG: CRITICAL: An unexpected error occurred during TimecodeUtils initialization:")
])
def test_init_timecode_utils_fails(mocker, error_type, log_message_fragment):
    """Test that initialization handles errors from TimecodeUtils gracefully."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    mocker.patch('resolve_integration.TimecodeUtils', side_effect=error_type)
    
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
    mocker.patch('resolve_integration.TimecodeUtils')
    
    integration = ResolveIntegration()
    assert integration.initialized is True

    integration.timeline = MagicMock()
    integration.timeline.GetSetting.return_value = 24.0
    integration.timeline.GetTrackCount.return_value = 3
    
    info = integration.get_current_timeline_info()
    
    assert info is not None
    assert info['frame_rate'] == 24.0
    assert info['track_count'] == 3

def test_get_subtitles_with_timecode_online(mocker):
    """Test get_subtitles_with_timecode in an online state."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    # CRITICAL: This patch prevents the real TimecodeUtils constructor from running.
    mocker.patch('resolve_integration.TimecodeUtils')
    
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
    
    subs = integration.get_subtitles_with_timecode(track_number=1)
    
    assert len(subs) == 1
    assert subs[0]['text'] == "Test Subtitle"
    assert subs[0]['in_timecode'] == "00:00:04,167"
    assert subs[0]['out_timecode'] == "00:00:08,333"
    assert integration.tc_utils.timecode_to_srt_format.call_count == 2

def test_get_subtitles_with_timecode_no_tc_utils(mocker):
    """Test get_subtitles_with_timecode when tc_utils has failed to initialize."""
    mocker.patch.object(ResolveIntegration, 'get_resolve', return_value=MagicMock())
    mocker.patch('resolve_integration.TimecodeUtils', side_effect=Exception("TC Init Error"))

    with patch('builtins.print') as mock_print:
        integration = ResolveIntegration()
        assert integration.initialized is False
        
        integration.timeline = MagicMock()
        integration.timeline.GetSetting.return_value = 24.0
        integration.timeline.GetItemListInTrack.return_value = [MagicMock()]
        
        result = integration.get_subtitles_with_timecode(1)
        
        assert result == []
        mock_print.assert_any_call("LOG: WARNING: TimecodeUtils not available.")

if __name__ == "__main__":
    pytest.main()
