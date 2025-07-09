# tests/test_ui.py
import pytest
import json
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from src.ui import SubvigatorWindow, NumericTreeWidgetItem

@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def window(qtbot, qapp):
    """Fixture to create a SubvigatorWindow instance."""
    mock_resolve_integration = MagicMock()
    win = SubvigatorWindow(resolve_integration=mock_resolve_integration)
    qtbot.addWidget(win)
    return win

def test_numeric_tree_widget_item_sorting(qapp):
    """Test the custom sorting logic of NumericTreeWidgetItem."""
    tree = QTreeWidget()
    item1 = NumericTreeWidgetItem(tree)
    item1.setText(0, "10")
    
    item2 = NumericTreeWidgetItem(tree)
    item2.setText(0, "2")
    
    item3 = NumericTreeWidgetItem(tree)
    item3.setText(0, "abc")

    # The __lt__ method is what we are testing here.
    assert (item2 < item1) is True
    assert (item1 < item2) is False
    # Test fallback to string comparison
    assert (item3 < item1) is False # 'abc' > '10' as strings
    assert (item1 < item3) is True

def test_window_init(window):
    """Test the initialization of the SubvigatorWindow."""
    assert window.windowTitle() == "xdd sub"
    assert window.central_widget is not None
    assert window.tree.columnCount() == 5
    assert window.search_type_combo.count() == 5

def test_populate_table_with_data(window):
    """Test populating the tree widget with subtitle data."""
    subs_data = [
        {'id': 1, 'text': 'Hello', 'in_timecode': '00:01', 'out_timecode': '00:02', 'in_frame': 10},
        {'id': 2, 'text': 'World', 'in_timecode': '00:03', 'out_timecode': '00:04', 'in_frame': 20},
    ]
    window.populate_table(subs_data=subs_data)
    assert window.tree.topLevelItemCount() == 2
    assert window.tree.topLevelItem(0).text(1) == "Hello"
    assert window.tree.topLevelItem(1).text(1) == "World"

def test_populate_table_no_data(window):
    """Test populating the table with no data."""
    window.populate_table(subs_data=[])
    assert window.tree.topLevelItemCount() == 0

def test_load_subtitles_from_json_success(window, tmp_path):
    """Test loading subtitles from a valid JSON file."""
    json_file = tmp_path / "subs.json"
    subs_data = [{'id': 1, 'text': 'Test'}]
    with open(json_file, 'w') as f:
        json.dump(subs_data, f)
        
    loaded_data = window.load_subtitles_from_json(str(json_file))
    assert loaded_data == subs_data

def test_load_subtitles_from_json_not_found(window):
    """Test loading from a non-existent JSON file."""
    with patch('builtins.print') as mock_print:
        data = window.load_subtitles_from_json("nonexistent.json")
        assert data == []
        mock_print.assert_called_once()

def test_load_subtitles_from_json_invalid_json(window, tmp_path):
    """Test loading from an invalid JSON file."""
    json_file = tmp_path / "invalid.json"
    with open(json_file, 'w') as f:
        f.write("{'invalid': json}")
        
    with patch('builtins.print') as mock_print:
        data = window.load_subtitles_from_json(str(json_file))
        assert data == []
        mock_print.assert_called_once()

@pytest.mark.parametrize("filter_type, filter_text, subtitle, should_match", [
    ('Contains', 'world', 'Hello world', True),
    ('Contains', 'World', 'Hello world', False), # Case-sensitive
    ('Exact', 'Hello', 'Hello', True),
    ('Exact', 'Hello', 'Hello ', False),
    ('Starts With', 'He', 'Hello', True),
    ('Starts With', 'he', 'Hello', False),
    ('Ends With', 'lo', 'Hello', True),
    ('Ends With', 'Lo', 'Hello', False),
    ('Wildcard', 'H*o', 'Hello', True),
    ('Wildcard', 'H*o', 'Hippo', True),
    ('Wildcard', 'H*p', 'Hippo', False),
])
def test_filter_tree(window, filter_type, filter_text, subtitle, should_match):
    """Test the filter_tree method with various filter types."""
    window.populate_table(subs_data=[{'text': subtitle}])
    window.search_text.setText(filter_text)
    window.search_type_combo.setCurrentText(filter_type)
    
    window.filter_tree(filter_text)
    
    item = window.tree.topLevelItem(0)
    assert item.isHidden() is not should_match

def test_filter_tree_no_text(window):
    """Test filter_tree with no filter text, should show all items."""
    window.populate_table(subs_data=[{'text': 'A'}, {'text': 'B'}])
    window.search_text.setText("")
    window.filter_tree("")
    assert window.tree.topLevelItem(0).isHidden() is False
    assert window.tree.topLevelItem(1).isHidden() is False

def test_filter_tree_wildcard_no_re(window, mocker):
    """Test wildcard filter when 're' module import fails."""
    mocker.patch('src.ui.re.search', side_effect=ImportError)
    window.populate_table(subs_data=[{'text': 'Hello'}])
    window.search_text.setText("H*o")
    window.search_type_combo.setCurrentText('Wildcard')
    window.filter_tree("H*o")
    # Fallback behavior is to show the item
    assert window.tree.topLevelItem(0).isHidden() is False

def test_export_subtitles_success(window, tmp_path, mocker):
    """Test successful export of subtitles to a JSON file."""
    subs_data = [{'id': 1, 'text': 'Export Test'}]
    window.subtitles_data = subs_data
    
    mock_file_dialog = mocker.patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',
                                    return_value=(str(tmp_path / "export.json"), "JSON (*.json)"))
    
    window.export_subtitles()
    
    mock_file_dialog.assert_called_once()
    with open(tmp_path / "export.json", 'r') as f:
        exported_data = json.load(f)
    assert exported_data == subs_data

def test_export_subtitles_no_data(window, mocker):
    """Test exporting when there is no subtitle data."""
    window.subtitles_data = []
    mock_file_dialog = mocker.patch('PySide6.QtWidgets.QFileDialog.getSaveFileName')
    
    window.export_subtitles()
    
    mock_file_dialog.assert_not_called()

def test_export_subtitles_exception_on_write(window, tmp_path, mocker):
    """Test exception handling during file write in export_subtitles."""
    window.subtitles_data = [{'id': 1}]
    mocker.patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',
                 return_value=(str(tmp_path / "export.json"), "JSON (*.json)"))
    
    mocker.patch('builtins.open', side_effect=IOError("Disk full"))
    mock_print = mocker.patch('builtins.print')
    
    window.export_subtitles()
    
    mock_print.assert_called_with("Failed to export subtitles: Disk full")

def test_export_subtitles_no_file_selected(window, mocker):
    """Test that nothing happens if the user cancels the file dialog."""
    mocker.patch('PySide6.QtWidgets.QFileDialog.getSaveFileName', return_value=("", ""))
    mock_open = mocker.patch('builtins.open')
    
    window.export_subtitles()
    
    mock_open.assert_not_called()

def test_numeric_tree_widget_item_sorting_type_error(qapp):
    """Test TypeError handling in NumericTreeWidgetItem sorting."""
    tree = QTreeWidget()
    item1 = NumericTreeWidgetItem(tree)
    item1.setText(0, "10")

    # A non-QTreeWidgetItem object
    other_item = "not a tree item"

    # This should not raise an exception, but return NotImplemented
    # which Python interprets as False for the less-than operation.
    with pytest.raises(TypeError):
        item1 < other_item

# --- Find and Replace Tests ---

@pytest.fixture
def populated_window(window):
    """Fixture to create a window with some subtitle data."""
    subs_data = [
        {'id': 1, 'text': 'Hello world, this is a test.'},
        {'id': 2, 'text': 'Another test line with world.'},
        {'id': 3, 'text': 'No matching text here.'},
        {'id': 4, 'text': 'world again, for wrapping.'},
    ]
    window.populate_table(subs_data=subs_data)
    return window

def test_find_next_simple_find(populated_window):
    """Test find_next functionality."""
    win = populated_window
    win.find_text.setText("world")
    
    # No item selected, should start from the top
    win.find_next()
    
    assert win.tree.currentItem() is not None
    assert win.tree.currentItem().text(1) == 'Hello world, this is a test.'
    
    # Find the next one
    win.find_next()
    assert win.tree.currentItem().text(1) == 'Another test line with world.'

def test_find_next_wrapping(populated_window):
    """Test that find_next wraps around to the beginning."""
    win = populated_window
    win.find_text.setText("world")

    # Manually set current item to the last match
    last_match_item = win.tree.findItems("world again", Qt.MatchContains, 1)[0] # Search in column 1
    win.tree.setCurrentItem(last_match_item)

    # This should wrap around and find the first item
    win.find_next()
    assert win.tree.currentItem() is not None
    assert win.tree.currentItem().text(1) == 'Hello world, this is a test.'

def test_find_next_no_match(populated_window):
    """Test find_next with text that doesn't exist."""
    win = populated_window
    win.find_text.setText("nonexistent")
    
    first_item = win.tree.topLevelItem(0)
    win.tree.setCurrentItem(first_item)
    
    win.find_next()
    
    # Current item should not change
    assert win.tree.currentItem() == first_item

def test_replace_current_and_find_next(populated_window):
    """Test replacing the current selection and moving to the next."""
    win = populated_window
    win.find_text.setText("world")
    win.replace_text.setText("planet")

    # Find the first item
    win.find_next()
    assert win.tree.currentItem().text(1) == 'Hello world, this is a test.'

    # Replace it
    win.replace_current()
    
    # Check that the text was replaced
    assert win.tree.topLevelItem(0).text(1) == 'Hello planet, this is a test.'
    
    # Check that it moved to the next item
    assert win.tree.currentItem().text(1) == 'Another test line with world.'

def test_replace_all_simple(populated_window):
    """Test the replace_all functionality."""
    win = populated_window
    win.find_text.setText("test")
    win.replace_text.setText("sample")
    
    win.replace_all()
    
    assert win.tree.topLevelItem(0).text(1) == 'Hello world, this is a sample.'
    assert win.tree.topLevelItem(1).text(1) == 'Another sample line with world.'
    assert win.tree.topLevelItem(2).text(1) == 'No matching text here.' # Should be unchanged

def test_find_and_replace_no_find_text(populated_window):
    """Test that find/replace functions do nothing if find_text is empty."""
    win = populated_window
    original_texts = [win.tree.topLevelItem(i).text(1) for i in range(win.tree.topLevelItemCount())]
    
    win.find_text.setText("")
    win.replace_text.setText("should not appear")
    
    # Test find_next
    win.find_next()
    assert win.tree.currentItem() is None

    # Test replace_current
    item = win.tree.topLevelItem(0)
    win.tree.setCurrentItem(item)
    win.replace_current()
    assert item.text(1) == original_texts[0]
    
    # Test replace_all
    win.replace_all()
    final_texts = [win.tree.topLevelItem(i).text(1) for i in range(win.tree.topLevelItemCount())]
    assert original_texts == final_texts

def test_on_search_text_changed_triggers_filter(window, mocker):
    """Test that changing search_text triggers filter_tree."""
    mock_filter_tree = mocker.patch.object(window, 'filter_tree')
    
    # Simulate user typing in the search box
    window.search_text.setText("hello")
    
    # The signal should call the method
    mock_filter_tree.assert_called_once_with("hello")

def test_on_find_text_changed_triggers_filter(window, mocker):
    """Test that changing find_text also triggers filter_tree."""
    mock_filter_tree = mocker.patch.object(window, 'filter_tree')
    
    # Simulate user typing in the find box
    window.find_text.setText("world")
    
    # The signal should call the method, verifying the new functionality
    mock_filter_tree.assert_called_once_with("world")

def test_find_text_filters_tree_view_live(populated_window, qtbot):
    """
    End-to-end test to ensure typing in the find_text box filters the tree view.
    """
    win = populated_window
    
    # Initially, all items are visible
    assert not win.tree.topLevelItem(2).isHidden()

    # Simulate user typing in the find box
    qtbot.keyClicks(win.find_text, "world")

    # Now, the item that doesn't contain "world" should be hidden
    assert win.tree.topLevelItem(0).isHidden() is False # 'Hello world, this is a test.'
    assert win.tree.topLevelItem(1).isHidden() is False # 'Another test line with world.'
    assert win.tree.topLevelItem(2).isHidden() is True  # 'No matching text here.'
    assert win.tree.topLevelItem(3).isHidden() is False # 'world again, for wrapping.'

    # Clear the text, all items should be visible again
    win.find_text.clear()
    assert not win.tree.topLevelItem(2).isHidden()