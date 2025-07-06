# test_main.py
import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock PySide6 modules before they are imported by the application code
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()

# Mock other dependencies
sys.modules['resolve_integration'] = MagicMock()
sys.modules['timecode_utils'] = MagicMock()
sys.modules['ui'] = MagicMock()

from main import ApplicationController, main

@pytest.fixture
def mock_dependencies(mocker):
    """Fixture to mock all external dependencies of ApplicationController."""
    mock_qapplication = mocker.patch('main.QApplication')
    mock_resolve_integration = mocker.patch('main.ResolveIntegration')
    mock_timecode_utils = mocker.patch('main.TimecodeUtils')
    mock_subvigator_window = mocker.patch('main.SubvigatorWindow')
    mock_sys_exit = mocker.patch('sys.exit')

    # Return the mocked classes/modules so they can be accessed in tests
    return {
        "QApplication": mock_qapplication,
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
    mocker.patch('main.QApplication')
    # Patch ResolveIntegration to raise the error
    mocker.patch('main.ResolveIntegration', side_effect=ImportError("Fusionscript not found"))
    # Patch sys.exit to prevent the test from exiting
    mock_exit = mocker.patch('sys.exit')
    # Patch print to check the error message
    mock_print = mocker.patch('builtins.print')

    # Instantiate the controller
    ApplicationController()

    # Verify that the error was printed and sys.exit was called
    mock_print.assert_called_once_with("Error: Fusionscript not found")
    mock_exit.assert_called_once_with(1)


def test_connect_signals(controller):
    """Test that UI signals are connected to the correct slots."""
    controller.connect_signals()
    controller.window.refresh_button.clicked.connect.assert_called_once_with(controller.refresh_data)
    controller.window.tree.itemClicked.connect.assert_called_once_with(controller.on_item_clicked)
    controller.window.search_text.returnPressed.connect.assert_called_once_with(controller.filter_subtitles)

def test_refresh_data_no_timeline_info(controller):
    """Test refresh_data when no timeline info is available."""
    controller.resolve_integration.get_current_timeline_info.return_value = None
    controller.refresh_data()
    controller.window.track_combo.clear.assert_not_called()

def test_refresh_data_with_timeline_info(controller):
    """Test refresh_data with valid timeline and subtitle data."""
    timeline_info = {'track_count': 2, 'frame_rate': 24.0}
    subtitles = [{'Content': 'Sub 1'}, {'Content': 'Sub 2'}]
    
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.resolve_integration.get_subtitles.return_value = subtitles

def test_init_with_existing_app_instance(mocker):
    """Test __init__ when a QApplication instance already exists."""
    # Patch all dependencies manually
    mock_qapp_class = mocker.patch('main.QApplication')
    mocker.patch('main.ResolveIntegration')
    mocker.patch('main.TimecodeUtils')
    mocker.patch('main.SubvigatorWindow')

    # Configure the mock for QApplication
    # Make instance() return a mock object
    mock_instance = MagicMock()
    mock_qapp_class.instance.return_value = mock_instance
    
    # Instantiate the controller
    controller = ApplicationController()
    
    # Check that instance() was called
    mock_qapp_class.instance.assert_called_once()
    
    # Check that the constructor (the mock class itself) was NOT called
    # because the first part of the 'or' was true
    mock_qapp_class.assert_not_called()
    
    # And check that the app was set to the mock instance
    assert controller.app == mock_instance

@patch('builtins.print')
def test_on_item_clicked_valid_item(mock_print, controller):
    """Test on_item_clicked with a valid item to navigate the timeline."""
    mock_item = MagicMock()
    mock_item.text.return_value = "12345" # start_frame
    
    timeline_info = {'frame_rate': 24.0}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.window.drop_frame_checkbox.isChecked.return_value = False
    controller.timecode_utils.timecode_from_frame.return_value = "00:08:34:09"

    controller.on_item_clicked(mock_item, 2) # column 2 is start_frame

    mock_item.text.assert_called_once_with(2)
    controller.timecode_utils.timecode_from_frame.assert_called_once_with(12345, 24.0, False)
    controller.resolve_integration.timeline.SetCurrentTimecode.assert_called_once_with("00:08:34:09")
    mock_print.assert_called_once_with("Navigated to timecode: 00:08:34:09")

def test_refresh_data_with_zero_tracks(controller):
    """Test refresh_data with zero tracks in the timeline."""
    timeline_info = {'track_count': 0, 'frame_rate': 24.0}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.window.track_combo.currentIndex.return_value = 0

    controller.refresh_data()

    controller.window.track_combo.clear.assert_called_once()
    controller.window.track_combo.addItem.assert_not_called()
    controller.resolve_integration.get_subtitles.assert_called_once_with(1)

def test_refresh_data_with_no_subtitles(controller):
    """Test refresh_data when there are no subtitles on the track."""
    timeline_info = {'track_count': 1, 'frame_rate': 24.0}
    controller.resolve_integration.get_current_timeline_info.return_value = timeline_info
    controller.resolve_integration.get_subtitles.return_value = []
    controller.window.track_combo.currentIndex.return_value = 0

    controller.refresh_data()

    controller.window.track_combo.clear.assert_called_once()
    controller.window.track_combo.addItem.assert_called_once_with("ST 1")
    controller.resolve_integration.get_subtitles.assert_called_once_with(1)
    
    # Check that populate_table is called with an empty dictionary
    controller.window.populate_table.assert_called_once_with({})

def test_on_item_clicked_invalid_item(controller):
    """Test on_item_clicked with an item that has no start frame text."""
    mock_item = MagicMock()
    mock_item.text.return_value = "" # Empty start_frame
    
    controller.on_item_clicked(mock_item, 2)
    
    controller.resolve_integration.get_current_timeline_info.assert_not_called()
    controller.timecode_utils.timecode_from_frame.assert_not_called()

def test_filter_subtitles_empty_search(controller):
    """Test filter_subtitles with an empty search string."""
    controller.window.search_text.text.return_value = ""
    mock_item = MagicMock()
    controller.window.tree.topLevelItemCount.return_value = 5 # more than 0
    controller.window.tree.topLevelItem.return_value = mock_item

    controller.filter_subtitles()

    # When search text is empty, we should un-hide all items and return.
    assert controller.window.tree.topLevelItem.call_count == 5
    mock_item.setHidden.assert_called_with(False)
    assert mock_item.setHidden.call_count == 5

def test_filter_subtitles_with_search_text_match(controller):
    """Test filter_subtitles with text that matches an item."""
    mock_item = MagicMock()
    mock_item.text.return_value = "This is a test subtitle"
    controller.window.tree.topLevelItemCount.return_value = 1
    controller.window.tree.topLevelItem.return_value = mock_item
    controller.window.search_text.text.return_value = "test"

    controller.filter_subtitles()

    mock_item.setHidden.assert_called_once_with(False)

def test_filter_subtitles_with_search_text_no_match(controller):
    """Test filter_subtitles with text that does not match an item."""
    mock_item = MagicMock()
    mock_item.text.return_value = "This is a subtitle"
    controller.window.tree.topLevelItemCount.return_value = 1
    controller.window.tree.topLevelItem.return_value = mock_item
    controller.window.search_text.text.return_value = "nomatch"

    controller.filter_subtitles()

    mock_item.setHidden.assert_called_once_with(True)

def test_run(controller):
    """Test the main run loop of the application."""
    with patch.object(controller, 'connect_signals') as mock_connect, \
         patch.object(controller, 'refresh_data') as mock_refresh:
        
        controller.run()

        mock_connect.assert_called_once()
        mock_refresh.assert_called_once()
        controller.window.show.assert_called_once()
        controller.app.exec.assert_called_once()
        # sys.exit should be called with the result of app.exec()
        sys.exit.assert_called_once_with(controller.app.exec.return_value)

@patch('main.ApplicationController')
def test_main(MockedApplicationController):
    """Test the main function."""
    main()
    MockedApplicationController.assert_called_once()
    MockedApplicationController.return_value.run.assert_called_once()