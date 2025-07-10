import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src to path to allow imports
sys.path.insert(0, './src')

from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from main import ApplicationController

@pytest.fixture
def mock_resolve_integration():
    mock = MagicMock()
    mock.get_current_timeline_info.return_value = {'frame_rate': 24.0}
    mock.timeline.SetCurrentTimecode.return_value = True
    return mock

@pytest.fixture
def mock_subtitle_manager():
    mock = MagicMock()
    mock.get_subtitles.return_value = [
        {'index': 1, 'start': '00:00:10,500', 'text': 'Subtitle 1'},
        {'index': 2, 'start': '00:00:20,000', 'text': 'Subtitle 2'},
    ]
    return mock

@pytest.fixture
def mock_timecode_utils(mock_resolve_integration):
    # This is a bit tricky because TimecodeUtils __init__ might need a real resolve object
    # For unit testing the controller, we can mock its methods directly.
    with patch('main.TimecodeUtils') as mock:
        instance = mock.return_value
        instance.timecode_to_frames.side_effect = lambda tc, fr: int(float(tc.replace(',', '.')) * fr) if ':' not in tc else int((int(tc.split(':')[0])*3600 + int(tc.split(':')[1])*60 + float(tc.split(':')[2].replace(',','.'))) * fr)
        instance.timecode_from_frame.side_effect = lambda fr, fr_rate: f"{int(fr/fr_rate/3600):02d}:{int(fr/fr_rate%3600/60):02d}:{int(fr/fr_rate%60):02d}:{int(fr%fr_rate):02d}"
        yield instance


@pytest.fixture
def mock_data_model():
    return MagicMock()

@pytest.fixture
def controller(mock_resolve_integration, mock_subtitle_manager, mock_data_model, mock_timecode_utils, qtbot):
    # Ensure QApplication instance exists
    QApplication.instance() or QApplication(sys.argv)
    
    # Mock the window and its components
    with patch('main.SubvigatorWindow') as mock_window:
        # We need a real QTreeWidget to test item interaction
        tree = QTreeWidget()
        qtbot.addWidget(tree)
        mock_window.return_value.tree = tree
        
        controller = ApplicationController(
            resolve_integration=mock_resolve_integration,
            subtitle_manager=mock_subtitle_manager,
            data_model=mock_data_model,
            timecode_utils=mock_timecode_utils
        )
        # Manually populate the tree for the test
        for sub in mock_subtitle_manager.get_subtitles():
            item = QTreeWidgetItem([str(sub['index']), sub['start'], sub['text']])
            controller.window.tree.addTopLevelItem(item)

        yield controller

def test_on_item_clicked_jumps_to_correct_timecode(controller, mock_resolve_integration, mock_timecode_utils):
    """
    Test that clicking a subtitle item in the UI triggers a timecode jump in Resolve.
    """
    # GIVEN an item in the tree
    item_to_click = controller.window.tree.topLevelItem(0) # First item: index 1, start '00:00:10,500'
    column_to_click = 0
    
    # WHEN the item is clicked
    controller.on_item_clicked(item_to_click, column_to_click)

    # THEN the timecode utilities are called with the correct parameters
    frame_rate = mock_resolve_integration.get_current_timeline_info()['frame_rate']
    mock_timecode_utils.timecode_to_frames.assert_called_once_with('00:00:10,500', frame_rate)
    
    # AND the resolve integration is called to set the new timecode
    # Calculation: (10s + 500ms) * 24fps = 10.5 * 24 = 252 frames
    # Converted back to timecode: 10s and 12 frames -> 00:00:10:12
    expected_frames = 252
    expected_resolve_tc = "00:00:10:12" 
    mock_timecode_utils.timecode_from_frame.assert_called_once_with(expected_frames, frame_rate)
    mock_resolve_integration.timeline.SetCurrentTimecode.assert_called_once_with(expected_resolve_tc)

def test_on_item_clicked_with_invalid_item_id(controller, mock_resolve_integration, capsys):
    """
    Test that clicking an item with a non-numeric ID does not cause a crash.
    """
    # GIVEN an item with an invalid ID
    item_to_click = QTreeWidgetItem(["invalid_id", "00:00:00,000", "some text"])
    controller.window.tree.addTopLevelItem(item_to_click)
    column_to_click = 0

    # WHEN the item is clicked
    controller.on_item_clicked(item_to_click, column_to_click)

    # THEN no timecode jump is attempted
    mock_resolve_integration.timeline.SetCurrentTimecode.assert_not_called()
    
    # AND a warning is logged
    captured = capsys.readouterr()
    assert "LOG: WARNING: Failed to process item click for ID invalid_id" in captured.out
    
def test_on_item_clicked_with_nonexistent_subtitle_object(controller, mock_resolve_integration, mock_subtitle_manager, capsys):
    """
    Test that clicking an item whose ID does not correspond to a subtitle object is handled gracefully.
    """
    # GIVEN an item with a valid but non-existent ID
    item_to_click = QTreeWidgetItem(["999", "00:00:00,000", "some text"])
    controller.window.tree.addTopLevelItem(item_to_click)
    column_to_click = 0

    # WHEN the item is clicked
    controller.on_item_clicked(item_to_click, column_to_click)

    # THEN no timecode jump is attempted
    mock_resolve_integration.timeline.SetCurrentTimecode.assert_not_called()
    
    # AND a warning is logged
    captured = capsys.readouterr()
    assert "LOG: WARNING: Failed to get subtitle object for ID 999" in captured.out
