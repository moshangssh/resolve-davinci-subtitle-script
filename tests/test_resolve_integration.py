import pytest
from unittest.mock import MagicMock, patch
import sys

# Add the current directory to the path to import the script
sys.path.append('.')
from resolve_integration import ResolveIntegration

@pytest.fixture
def mock_resolve_objects():
    """Fixture for a fully mocked Resolve object hierarchy."""
    mock_resolve_app = MagicMock(name="ResolveApp")
    mock_project_manager = MagicMock(name="ProjectManager")
    mock_project = MagicMock(name="Project")
    mock_timeline = MagicMock(name="Timeline")

    mock_resolve_app.GetProjectManager.return_value = mock_project_manager
    mock_project_manager.GetCurrentProject.return_value = mock_project
    mock_project.GetCurrentTimeline.return_value = mock_timeline
    
    return mock_resolve_app, mock_project_manager, mock_project, mock_timeline

# --- Tests for __init__ ---
def test_initialization_success(mock_resolve_objects):
    """Test successful initialization of ResolveIntegration."""
    mock_resolve_app, pm, proj, timeline = mock_resolve_objects
    
    with patch.object(ResolveIntegration, '_get_resolve_instance', return_value=mock_resolve_app) as mock_get_instance:
        integration = ResolveIntegration()
        
        mock_get_instance.assert_called_once()
        assert integration.resolve is mock_resolve_app
        assert integration.project_manager is pm
        assert integration.project is proj
        assert integration.timeline is timeline
        mock_resolve_app.GetProjectManager.assert_called_once()
        pm.GetCurrentProject.assert_called_once()
        proj.GetCurrentTimeline.assert_called_once()

def test_initialization_failure():
    """Test initialization failure when connection to Resolve fails."""
    with patch.object(ResolveIntegration, '_get_resolve_instance', return_value=None) as mock_get_instance:
        with pytest.raises(ImportError, match="Could not connect to DaVinci Resolve"):
            ResolveIntegration()
        mock_get_instance.assert_called_once()

# --- Tests for _get_resolve_instance ---
def test_get_resolve_instance_with_fusionscript():
    """Test _get_resolve_instance successfully imports fusionscript."""
    mock_fusionscript = MagicMock()
    with patch.dict('sys.modules', {'fusionscript': mock_fusionscript, 'DaVinciResolveScript': None}):
        integration = object.__new__(ResolveIntegration)
        instance = integration._get_resolve_instance()
        
        assert instance == mock_fusionscript.scriptapp.return_value
        mock_fusionscript.scriptapp.assert_called_with("Resolve")

def test_get_resolve_instance_with_davinciresolvescript():
    """Test _get_resolve_instance falls back to DaVinciResolveScript."""
    mock_dvr_script = MagicMock()
    with patch.dict('sys.modules', {'fusionscript': None, 'DaVinciResolveScript': mock_dvr_script}):
        integration = object.__new__(ResolveIntegration)
        instance = integration._get_resolve_instance()

        assert instance == mock_dvr_script.scriptapp.return_value
        mock_dvr_script.scriptapp.assert_called_with("Resolve")

def test_get_resolve_instance_failure():
    """Test _get_resolve_instance returns None when both imports fail."""
    with patch.dict('sys.modules', {'fusionscript': None, 'DaVinciResolveScript': None}):
        integration = object.__new__(ResolveIntegration)
        instance = integration._get_resolve_instance()
        assert instance is None

# --- Tests for other methods ---
@patch('resolve_integration.ResolveIntegration.__init__', lambda x: None)
def test_get_current_timeline_info_success(mock_resolve_objects):
    """Test get_current_timeline_info returns correct data."""
    _, _, _, mock_timeline = mock_resolve_objects
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline
    
    mock_timeline.GetSetting.return_value = 24.0
    mock_timeline.GetTrackCount.return_value = 2

    info = integration.get_current_timeline_info()
    
    assert info == {'frame_rate': 24.0, 'track_count': 2}
    mock_timeline.GetSetting.assert_called_once_with('timelineFrameRate')
    mock_timeline.GetTrackCount.assert_called_once_with('subtitle')

@patch('resolve_integration.ResolveIntegration.__init__', lambda x: None)
def test_get_current_timeline_info_no_timeline():
    """Test get_current_timeline_info returns None when there is no timeline."""
    integration = ResolveIntegration()
    integration.timeline = None
    
    info = integration.get_current_timeline_info()
    assert info is None

@patch('resolve_integration.ResolveIntegration.__init__', lambda x: None)
def test_get_subtitles_success(mock_resolve_objects):
    """Test get_subtitles returns a list of subtitles."""
    _, _, _, mock_timeline = mock_resolve_objects
    
    integration = ResolveIntegration()
    integration.timeline = mock_timeline
    
    expected_subtitles = ["Subtitle 1", "Subtitle 2"]
    mock_timeline.GetItemListInTrack.return_value = expected_subtitles

    subtitles = integration.get_subtitles(track_number=2)
    
    assert subtitles == expected_subtitles
    mock_timeline.GetItemListInTrack.assert_called_once_with('subtitle', 2)

@patch('resolve_integration.ResolveIntegration.__init__', lambda x: None)
def test_get_subtitles_no_timeline():
    """Test get_subtitles returns an empty list when there is no timeline."""
    integration = ResolveIntegration()
    integration.timeline = None
    
    subtitles = integration.get_subtitles()
    assert subtitles == []