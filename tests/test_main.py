# test_main.py
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add both the project root and the src directory to the Python path
# This allows tests to import from 'src.main' and for 'src.main' to import its siblings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


# We will now mock QApplication directly in fixtures where needed, instead of globally.
# This avoids the fatal errors seen with pytest-qt interactions.
from src.main import ApplicationController, main

@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to mock all external dependencies of ApplicationController."""
    # Mock QApplication to avoid creating a real instance
    mock_qapplication_class = mocker.patch('src.main.QApplication')
    mock_qapplication_instance = MagicMock()
    mock_qapplication_class.instance.return_value = None # Simulate no existing instance
    mock_qapplication_class.return_value = mock_qapplication_instance # Return a mock when instantiated

    # Since src/main.py uses "from resolve_integration...", we patch it from main's perspective
    mock_resolve_integration = mocker.patch('src.main.ResolveIntegration')
    mock_timecode_utils = mocker.patch('src.main.TimecodeUtils')
    mock_subvigator_window = mocker.patch('src.main.SubvigatorWindow')
    mock_sys_exit = mocker.patch('sys.exit')

    return {
        "QApplication": mock_qapplication_class,
        "ResolveIntegration": mock_resolve_integration,
        "TimecodeUtils": mock_timecode_utils,
        "SubvigatorWindow": mock_subvigator_window,
        "sys_exit": mock_sys_exit
    }

@pytest.fixture
def controller(mock_dependencies):
    """Fixture to create an ApplicationController instance with mocked dependencies."""
    return ApplicationController()

def test_application_controller_init_success(controller, mock_dependencies):
    """Test successful initialization of ApplicationController."""
    mock_dependencies["QApplication"].assert_called_with(sys.argv)
    mock_dependencies["ResolveIntegration"].assert_called_once()
    mock_dependencies["TimecodeUtils"].assert_called_once_with(
        mock_dependencies["ResolveIntegration"].return_value.resolve
    )
    mock_dependencies["SubvigatorWindow"].assert_called_once()
    assert controller.app is not None
    assert controller.resolve_integration is not None
    assert controller.timecode_utils is not None
    assert controller.window is not None

def test_application_controller_init_import_error(mocker):
    """Test ApplicationController initialization when ResolveIntegration raises ImportError."""
    mocker.patch('src.main.QApplication')
    mocker.patch('src.main.ResolveIntegration', side_effect=ImportError("Fusionscript not found"))
    mock_exit = mocker.patch('sys.exit')
    mock_print = mocker.patch('builtins.print')

    ApplicationController()

    mock_print.assert_called_once_with("Error: Fusionscript not found")
    mock_exit.assert_called_once_with(1)

def test_connect_signals(controller):
    """Test that UI signals are connected to the correct slots."""
    controller.connect_signals()
    controller.window.refresh_button.clicked.connect.assert_called_once_with(controller.refresh_data)
    controller.window.tree.itemClicked.connect.assert_called_once_with(controller.on_item_clicked)
    controller.window.search_text.returnPressed.connect.assert_called_once_with(controller.filter_subtitles)
    controller.window.track_combo.currentIndexChanged.connect.assert_called_once_with(controller.on_track_changed)

def test_refresh_data_no_timeline_info(controller):
    """Test refresh_data when no timeline info is available."""
    controller.resolve_integration.get_current_timeline_info.return_value = None
    controller.refresh_data()
    controller.window.track_combo.clear.assert_not_called()

def test_refresh_data_with_timeline_info(controller):
    """Test refresh_data with valid timeline and subtitle data."""
    timeline_info = {'track_count': 2, 'frame_rate': 24.0}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.window.track_combo.count.return_value = 2

    with patch.object(controller, 'on_track_changed') as mock_on_track_changed:
        controller.refresh_data()
        controller.window.track_combo.clear.assert_called_once()
        assert controller.window.track_combo.addItem.call_count == 2
        mock_on_track_changed.assert_called_once()

def test_init_with_existing_app_instance(mocker):
    """Test __init__ when a QApplication instance already exists."""
    mock_qapp_class = mocker.patch('src.main.QApplication')
    mock_instance = MagicMock()
    mock_qapp_class.instance.return_value = mock_instance
    mocker.patch('src.main.ResolveIntegration')
    mocker.patch('src.main.TimecodeUtils')
    mocker.patch('src.main.SubvigatorWindow')

    controller = ApplicationController()

    mock_qapp_class.instance.assert_called_once()
    mock_qapp_class.assert_not_called() # Constructor should not be called
    assert controller.app == mock_instance

@patch('builtins.print')
def test_on_item_clicked_valid_item(mock_print, controller):
    """Test on_item_clicked with a valid item to navigate the timeline."""
    mock_item = MagicMock()
    mock_item.text.return_value = "12345"
    timeline_info = {'frame_rate': 24.0}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.window.drop_frame_checkbox.isChecked.return_value = False
    controller.timecode_utils.timecode_from_frame.return_value = "00:08:34:09"

    controller.on_item_clicked(mock_item, 2)

    controller.timecode_utils.timecode_from_frame.assert_called_once_with(12345, 24.0, False)
    controller.resolve_integration.timeline.SetCurrentTimecode.assert_called_once_with("00:08:34:09")

def test_on_item_clicked_invalid_item(controller):
    """Test on_item_clicked with an item that has no start frame text."""
    mock_item = MagicMock()
    mock_item.text.return_value = ""
    controller.on_item_clicked(mock_item, 2)
    controller.resolve_integration.get_current_timeline_info.assert_not_called()

def test_filter_subtitles_empty_search(controller):
    """Test filter_subtitles with an empty search string."""
    controller.window.search_text.text.return_value = ""
    mock_item = MagicMock()
    controller.window.tree.topLevelItemCount.return_value = 1
    controller.window.tree.topLevelItem.return_value = mock_item
    controller.filter_subtitles()
    mock_item.setHidden.assert_called_with(False)

def test_filter_subtitles_with_search_text_match(controller):
    """Test filter_subtitles with text that matches an item."""
    mock_item = MagicMock()
    mock_item.text.return_value = "This is a test subtitle"
    controller.window.tree.topLevelItemCount.return_value = 1
    controller.window.tree.topLevelItem.return_value = mock_item
    controller.window.search_text.text.return_value = "test"
    controller.filter_subtitles()
    mock_item.setHidden.assert_called_with(False)

def test_filter_subtitles_with_search_text_no_match(controller):
    """Test filter_subtitles with text that does not match an item."""
    mock_item = MagicMock()
    mock_item.text.return_value = "This is a subtitle"
    controller.window.tree.topLevelItemCount.return_value = 1
    controller.window.tree.topLevelItem.return_value = mock_item
    controller.window.search_text.text.return_value = "nomatch"
    controller.filter_subtitles()
    mock_item.setHidden.assert_called_with(True)

def test_run(controller):
    """Test the main run loop of the application."""
    with patch.object(controller, 'connect_signals') as mock_connect, \
         patch.object(controller, 'refresh_data') as mock_refresh:
        controller.run()
        mock_connect.assert_called_once()
        mock_refresh.assert_called_once()
        controller.window.show.assert_called_once()
        controller.app.exec.assert_called_once()
        sys.exit.assert_called_once_with(controller.app.exec.return_value)

@patch('src.main.ApplicationController')
def test_main(MockedApplicationController):
    """Test the main function."""
    main()
    MockedApplicationController.assert_called_once()
    MockedApplicationController.return_value.run.assert_called_once()

def test_on_track_changed_valid_index(controller):
    """Test on_track_changed when a valid track is selected."""
    controller.window.track_combo.currentIndex.return_value = 1
    subs = [{'Content': 'Sub 1'}, {'Content': 'Sub 2'}]
    controller.resolve_integration.get_subtitles.return_value = subs
    controller.on_track_changed()
    controller.resolve_integration.get_subtitles.assert_called_once_with(2)
    expected_subs_data = {1: subs[0], 2: subs[1]}
    controller.window.populate_table.assert_called_once_with(expected_subs_data)

def test_on_track_changed_no_subtitles(controller):
    """Test on_track_changed when the selected track has no subtitles."""
    controller.window.track_combo.currentIndex.return_value = 0
    controller.resolve_integration.get_subtitles.return_value = []
    controller.on_track_changed()
    controller.resolve_integration.get_subtitles.assert_called_once_with(1)
    controller.window.populate_table.assert_called_once_with({})

def test_on_track_changed_at_index_zero_should_return(controller):
    """Test that on_track_changed returns early if current index is invalid."""
    controller.window.track_combo.currentIndex.return_value = -1
    controller.on_track_changed()
    controller.resolve_integration.get_subtitles.assert_not_called()

def test_refresh_data_manually_triggers_on_track_changed(controller):
    """Test that refresh_data triggers on_track_changed for the initial load."""
    timeline_info = {'track_count': 1}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.window.track_combo.count.return_value = 1
    with patch.object(controller, 'on_track_changed') as mock_on_track_changed:
        controller.refresh_data()
        mock_on_track_changed.assert_called_once()

def test_refresh_data_with_no_tracks_does_not_trigger_change(controller):
    """Test that on_track_changed is not called if there are no tracks."""
    timeline_info = {'track_count': 0}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.window.track_combo.count.return_value = 0
    with patch.object(controller, 'on_track_changed') as mock_on_track_changed:
        controller.refresh_data()
        mock_on_track_changed.assert_not_called()