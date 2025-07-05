import unittest
from unittest.mock import MagicMock, patch, mock_open

# Add the subvigator directory to the path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from subvigator.resolve_integration import ResolveIntegration

class TestResolveIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a mock for the Resolve API."""
        self.mock_resolve = MagicMock()
        self.mock_project_manager = MagicMock()
        self.mock_project = MagicMock()
        self.mock_timeline = MagicMock()

        self.mock_resolve.GetProjectManager.return_value = self.mock_project_manager
        self.mock_project_manager.GetCurrentProject.return_value = self.mock_project
        self.mock_project.GetCurrentTimeline.return_value = self.mock_timeline

        # Mock the modules that provide the Resolve instance
        self.mock_fusionscript = MagicMock()
        self.mock_fusionscript.scriptapp.return_value = self.mock_resolve
        self.mock_dvr_script = MagicMock()
        self.mock_dvr_script.scriptapp.return_value = self.mock_resolve

        # Patch the import system
        self.patched_fusionscript = patch.dict('sys.modules', {'fusionscript': self.mock_fusionscript})
        self.patched_dvr_script = patch.dict('sys.modules', {'DaVinciResolveScript': self.mock_dvr_script})

    def test_initialization_success_with_fusionscript(self):
        """Test successful initialization using fusionscript."""
        with self.patched_fusionscript:
            # Ensure DaVinciResolveScript is not found
            with patch.dict('sys.modules', {'DaVinciResolveScript': None}):
                integration = ResolveIntegration()
                self.assertIsNotNone(integration.resolve)
                self.assertEqual(integration.project_manager, self.mock_project_manager)
                self.assertEqual(integration.project, self.mock_project)
                self.assertEqual(integration.timeline, self.mock_timeline)
                self.mock_fusionscript.scriptapp.assert_called_with("Resolve")

    def test_initialization_success_with_dvr_script(self):
        """Test successful initialization using DaVinciResolveScript as a fallback."""
        # Make fusionscript import fail
        with patch.dict('sys.modules', {'fusionscript': None}):
            with self.patched_dvr_script:
                integration = ResolveIntegration()
                self.assertIsNotNone(integration.resolve)
                self.mock_dvr_script.scriptapp.assert_called_with("Resolve")


    def test_initialization_failure(self):
        """Test initialization failure when no scripting module is found."""
        with patch.dict('sys.modules', {'fusionscript': None, 'DaVinciResolveScript': None}):
            with self.assertRaises(ImportError) as context:
                ResolveIntegration()
            self.assertEqual(str(context.exception), "Could not connect to DaVinci Resolve. Make sure the application is running.")

    def test_get_current_timeline_info(self):
        """Test getting timeline info when a timeline is present."""
        self.mock_timeline.GetSetting.return_value = 24
        self.mock_timeline.GetTrackCount.return_value = 2
        
        with self.patched_fusionscript:
            integration = ResolveIntegration()
            info = integration.get_current_timeline_info()
            self.assertEqual(info, {'frame_rate': 24, 'track_count': 2})
            self.mock_timeline.GetSetting.assert_called_with('timelineFrameRate')
            self.mock_timeline.GetTrackCount.assert_called_with('subtitle')

    def test_get_current_timeline_info_no_timeline(self):
        """Test getting timeline info when there is no timeline."""
        self.mock_project.GetCurrentTimeline.return_value = None
        with self.patched_fusionscript:
            integration = ResolveIntegration()
            info = integration.get_current_timeline_info()
            self.assertIsNone(info)

    def test_get_subtitles(self):
        """Test getting subtitles from a specific track."""
        mock_subtitle_item = MagicMock()
        mock_subtitle_item.GetName.return_value = "Test Subtitle"
        self.mock_timeline.GetItemListInTrack.return_value = [mock_subtitle_item]

        with self.patched_fusionscript:
            integration = ResolveIntegration()
            subtitles = integration.get_subtitles(track_number=1)
            self.assertEqual(len(subtitles), 1)
            self.assertEqual(subtitles[0].GetName(), "Test Subtitle")
            self.mock_timeline.GetItemListInTrack.assert_called_with('subtitle', 1)

    def test_get_subtitles_no_timeline(self):
        """Test getting subtitles when there is no timeline."""
        self.mock_project.GetCurrentTimeline.return_value = None
        with self.patched_fusionscript:
            integration = ResolveIntegration()
            subtitles = integration.get_subtitles()
            self.assertEqual(subtitles, [])

if __name__ == '__main__':
    unittest.main()