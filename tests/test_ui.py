# tests/test_ui.py
import pytest
import json
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
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
    win = SubvigatorWindow()
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
    
    window.filter_tree()
    
    item = window.tree.topLevelItem(0)
    assert item.isHidden() is not should_match

def test_filter_tree_no_text(window):
    """Test filter_tree with no filter text, should show all items."""
    window.populate_table(subs_data=[{'text': 'A'}, {'text': 'B'}])
    window.search_text.setText("")
    window.filter_tree()
    assert window.tree.topLevelItem(0).isHidden() is False
    assert window.tree.topLevelItem(1).isHidden() is False

def test_filter_tree_wildcard_no_re(window, mocker):
    """Test wildcard filter when 're' module import fails."""
    mocker.patch('src.ui.re.search', side_effect=ImportError)
    window.populate_table(subs_data=[{'text': 'Hello'}])
    window.search_text.setText("H*o")
    window.search_type_combo.setCurrentText('Wildcard')
    window.filter_tree()
    # Fallback behavior is to show the item
    assert window.tree.topLevelItem(0).isHidden() is False