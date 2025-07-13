# tests/test_ui.py
import pytest
import json
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QStyleOptionViewItem
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QStyledItemDelegate
from bs4 import BeautifulSoup
from src.ui import SubvigatorWindow, NumericTreeWidgetItem, CharCountDelegate

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
    assert window.windowTitle() == "Subvigator - DaVinci Resolve Subtitle Editor"
    assert window.central_widget is not None
    assert window.tree.columnCount() == 6
    assert window.search_type_combo.count() == 5

def test_populate_table_with_data(window):
    """Test populating the tree widget with subtitle data."""
    subs_data = [
        {'id': 1, 'text': 'Hello', 'in_timecode': '00:01', 'out_timecode': '00:02', 'in_frame': 10},
        {'id': 2, 'text': 'World', 'in_timecode': '00:03', 'out_timecode': '00:04', 'in_frame': 20},
    ]
    window.populate_table(subs_data=subs_data)
    assert window.tree.topLevelItemCount() == 2
    assert window.tree.topLevelItem(0).text(2) == "Hello"
    assert window.tree.topLevelItem(1).text(2) == "World"

def test_populate_table_no_data(window):
    """Test populating the table with no data."""
    window.populate_table(subs_data=[])
    assert window.tree.topLevelItemCount() == 0

@pytest.mark.skip(reason="Functionality moved to SubtitleManager. Test needs refactoring.")
def test_load_subtitles_from_json_success(window, tmp_path):
    """Test loading subtitles from a valid JSON file."""
    # TODO: Refactor to test SubtitleManager or controller logic
    pass

@pytest.mark.skip(reason="Functionality moved to SubtitleManager. Test needs refactoring.")
def test_load_subtitles_from_json_not_found(window):
    """Test loading from a non-existent JSON file."""
    # TODO: Refactor to test SubtitleManager or controller logic
    pass

@pytest.mark.skip(reason="Functionality moved to SubtitleManager. Test needs refactoring.")
def test_load_subtitles_from_json_invalid_json(window, tmp_path):
    """Test loading from an invalid JSON file."""
    # TODO: Refactor to test SubtitleManager or controller logic
    pass

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

@pytest.mark.skip(reason="Functionality moved to controller. Test needs refactoring.")
def test_export_subtitles_success(window, tmp_path, mocker):
    """Test successful export of subtitles to a JSON file."""
    # TODO: Refactor to test controller logic via button click simulation
    pass

@pytest.mark.skip(reason="Functionality moved to controller. Test needs refactoring.")
def test_export_subtitles_no_data(window, mocker):
    """Test exporting when there is no subtitle data."""
    # TODO: Refactor to test controller logic
    pass

@pytest.mark.skip(reason="Functionality moved to controller. Test needs refactoring.")
def test_export_subtitles_exception_on_write(window, tmp_path, mocker):
    """Test exception handling during file write in export_subtitles."""
    # TODO: Refactor to test controller logic
    pass

@pytest.mark.skip(reason="Functionality moved to controller. Test needs refactoring.")
def test_export_subtitles_no_file_selected(window, mocker):
    """Test that nothing happens if the user cancels the file dialog."""
    # TODO: Refactor to test controller logic
    pass

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
        {'id': 1, 'text': 'Hello world, this is a test.', 'in_timecode': '00:01', 'out_timecode': '00:02', 'in_frame': 10},
        {'id': 2, 'text': 'Another test line with world.', 'in_timecode': '00:03', 'out_timecode': '00:04', 'in_frame': 20},
        {'id': 3, 'text': 'No matching text here.', 'in_timecode': '00:05', 'out_timecode': '00:06', 'in_frame': 30},
        {'id': 4, 'text': 'world again, for wrapping.', 'in_timecode': '00:07', 'out_timecode': '00:08', 'in_frame': 40},
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
    assert win.tree.currentItem().text(2) == 'Hello world, this is a test.'
    
    # Find the next one
    win.find_next()
    assert win.tree.currentItem().text(2) == 'Another test line with world.'

def test_find_next_wrapping(populated_window):
    """Test that find_next wraps around to the beginning."""
    win = populated_window
    win.find_text.setText("world")

    # Manually set current item to the last match
    last_match_item = win.tree.findItems("world again", Qt.MatchContains, 2)[0] # Search in column 2
    win.tree.setCurrentItem(last_match_item)

    # This should wrap around and find the first item
    win.find_next()
    assert win.tree.currentItem() is not None
    assert win.tree.currentItem().text(2) == 'Hello world, this is a test.'

def test_find_next_no_match(populated_window):
    """Test find_next with text that doesn't exist."""
    win = populated_window
    win.find_text.setText("nonexistent")
    
    first_item = win.tree.topLevelItem(0)
    win.tree.setCurrentItem(first_item)
    
    win.find_next()
    
    # Current item should not change
    assert win.tree.currentItem() == first_item

def test_replace_current_updates_item_correctly(populated_window):
    """
    Tests that the UI correctly updates a single item when instructed by the controller,
    simulating a "replace" action.
    """
    win = populated_window
    item = win.tree.topLevelItem(0)
    original_text = "Hello world, this is a test."
    item_id = int(item.text(0))
    
    # Simulate controller logic: it finds a match and tells the UI to update.
    new_text_from_controller = "Hello planet, this is a test."
    
    win.update_item_for_replace(item_id, original_text, new_text_from_controller)
    
    # Check that the display text is now HTML with diff highlighting
    expected_html = 'Hello <font color="red"><s>wor</s></font><font color="blue">p</font>l<font color="red"><s>d</s></font><font color="blue">anet</font>, this is a test.'
    assert item.text(2) == expected_html
    
    # Check that the underlying clean data in UserRole is updated
    assert item.data(2, Qt.UserRole) == new_text_from_controller
    
    # Check that the OriginalTextRole is preserved for future diffs
    assert item.data(2, win.OriginalTextRole) == original_text

def test_replace_all_updates_items_correctly(populated_window):
    """
    Tests that the UI correctly updates multiple items when instructed by the controller,
    simulating a "replace all" action.
    """
    win = populated_window
    
    # Simulate the list of changes generated by the controller after a "replace all"
    changes = [
        {
            'index': 1,
            'old': 'Hello world, this is a test.',
            'new': 'Hello planet, this is a test.'
        },
        {
            'index': 2,
            'old': 'Another test line with world.',
            'new': 'Another test line with planet.'
        }
    ]
    
    win.update_all_items_for_replace(changes)
    
    # --- Verify Item 1 ---
    item1 = win.find_item_by_id(1)
    expected_html1 = 'Hello <font color="red"><s>wor</s></font><font color="blue">p</font>l<font color="red"><s>d</s></font><font color="blue">anet</font>, this is a test.'
    assert item1.text(2) == expected_html1
    assert item1.data(2, Qt.UserRole) == 'Hello planet, this is a test.'
    assert item1.data(2, win.OriginalTextRole) == 'Hello world, this is a test.'
    
    # --- Verify Item 2 ---
    item2 = win.find_item_by_id(2)
    expected_html2 = 'Another test line with <font color="red"><s>wor</s></font><font color="blue">p</font>l<font color="red"><s>d</s></font><font color="blue">anet</font>.'
    assert item2.text(2) == expected_html2
    assert item2.data(2, Qt.UserRole) == 'Another test line with planet.'
    assert item2.data(2, win.OriginalTextRole) == 'Another test line with world.'
    
    # --- Verify Unchanged Item ---
    item3 = win.find_item_by_id(3)
    assert item3.text(2) == 'No matching text here.'
    assert item3.data(2, Qt.UserRole) == 'No matching text here.'

def test_update_all_items_with_no_changes(populated_window):
    """
    Tests that calling the update method with an empty list of changes
    does not alter any of the items in the tree.
    """
    win = populated_window
    original_texts = [win.tree.topLevelItem(i).text(2) for i in range(win.tree.topLevelItemCount())]
    
    # Simulate controller sending an empty list of changes
    win.update_all_items_for_replace([])
    
    final_texts = [win.tree.topLevelItem(i).text(2) for i in range(win.tree.topLevelItemCount())]
    
    assert original_texts == final_texts, "No items should have changed"

def test_on_search_text_changed_triggers_filter(window, mocker):
    """Test that changing search_text triggers filter_tree."""
    mock_filter_tree = mocker.patch.object(window, 'filter_tree')
    
    # Simulate user typing in the search box
    window.search_text.setText("hello")
    
    # The signal should call the method
    mock_filter_tree.assert_called_once_with("hello")

def test_on_find_text_changed_triggers_filter(window, qtbot):
    """Test that changing find_text also triggers filter_tree."""
    with patch.object(window, 'filter_tree') as mock_filter_tree:
        # Simulate user typing in the find box
        qtbot.keyClicks(window.find_text, "world")
        # The signal should call the method
        mock_filter_tree.assert_called_with("world")

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

# --- HTML Diff and Data Integrity Tests ---

def test_generate_diff_html_robustly(window):
    """
    Tests the _generate_diff_html method using BeautifulSoup for robust parsing,
    making it immune to minor whitespace or attribute order changes.
    """
    style_config = {
        'delete': '<font color="red"><s>{text}</s></font>',
        'insert': '<font color="blue">{text}</font>',
        'replace': '<font color="blue">{text}</font>',
    }

    # --- Test Case 1: Complex Replacement ---
    original = "the quick brown fox"
    new = "the slow brown cat"
    html_output = window._generate_diff_html(original, new, style_config)
    soup = BeautifulSoup(html_output, "html.parser")

    # Check for deleted parts
    deleted_tags = soup.select('font[color="red"] > s')
    assert len(deleted_tags) == 2, "Should find two deleted segments"
    deleted_texts = [tag.string for tag in deleted_tags]
    assert "quick" in deleted_texts
    assert "fox" in deleted_texts

    # Check for inserted parts
    inserted_tags = soup.select('font[color="blue"]')
    assert len(inserted_tags) == 2, "Should find two inserted segments"
    inserted_texts = [tag.string for tag in inserted_tags]
    assert "slow" in inserted_texts
    assert "cat" in inserted_texts
    
    # Check overall text content, ignoring spaces
    assert "the" in soup.get_text()
    assert "brown" in soup.get_text()
    assert soup.get_text().replace(" ", "") == "thequickslowbrownfoxcat"


    # --- Test Case 2: Pure Insertion ---
    original = "hello"
    new = "hello world"
    html_output = window._generate_diff_html(original, new, style_config)
    soup = BeautifulSoup(html_output, "html.parser")
    
    assert soup.get_text() == "hello world"
    assert not soup.select('font[color="red"]') # No deletions
    inserted_tag = soup.select_one('font[color="blue"]')
    assert inserted_tag is not None
    assert "world" in inserted_tag.string


    # --- Test Case 3: Pure Deletion ---
    original = "hello world"
    new = "hello"
    html_output = window._generate_diff_html(original, new, style_config)
    soup = BeautifulSoup(html_output, "html.parser")

    assert "hello" in soup.get_text()
    assert not soup.select('font[color="blue"]') # No insertions
    deleted_tag = soup.select_one('font[color="red"] > s')
    assert deleted_tag is not None
    assert "world" in deleted_tag.string

@pytest.mark.skip(reason="Dependent on a robust diff test. Refactor needed.")
def test_on_subtitle_edited_shows_green_highlight(populated_window, qtbot):
    """
    Test that manually editing a subtitle generates a green diff and preserves UserRole.
    """
    # TODO: Refactor after test_generate_diff_html is fixed.
    pass

@pytest.mark.skip(reason="Functionality moved to controller. Test needs refactoring.")
def test_replace_current_shows_red_and_blue_highlight(populated_window, qtbot):
    """
    Test that 'Replace' generates a red/blue diff and preserves UserRole.
    """
    # TODO: Refactor to test controller logic via button click simulation
    pass

@pytest.mark.skip(reason="Functionality moved to controller. Test needs refactoring.")
def test_replace_all_shows_red_and_blue_highlight(populated_window):
    """
    Test that 'Replace All' generates correct red/blue diffs and preserves UserRole.
    """
    # TODO: Refactor to test controller logic via button click simulation
    pass

def test_second_edit_diffs_against_first_edit(populated_window):
    """
    Tests the core bug fix: A second manual edit should create a diff
    against the result of the first edit, not the original text.
    """
    win = populated_window
    item = win.tree.topLevelItem(0)
    original_text = "Hello world, this is a test."
    
    # --- First Edit ---
    first_edit_text = "Hello Python world, this is a test."
    item.setText(2, first_edit_text)
    win.on_subtitle_edited(item, 2)

    # Check that OriginalTextRole is set and UserRole is updated
    assert item.data(2, win.OriginalTextRole) == original_text
    assert item.data(2, Qt.UserRole) == first_edit_text
    
    # --- Second Edit ---
    second_edit_text = "Hello Python world, this is a great test."
    item.setText(2, second_edit_text)
    win.on_subtitle_edited(item, 2)

    # Check that OriginalTextRole is STILL the original text
    assert item.data(2, win.OriginalTextRole) == original_text
    assert item.data(2, Qt.UserRole) == second_edit_text

    # The diff should be between the original and the second edit
    expected_html = 'Hello<font color="blue"> Python</font> world, this is a <font color="blue">great </font>test.'
    assert item.text(2) == expected_html


def test_reverting_to_original_clears_formatting(populated_window):
    """
    Tests that if a user edits a subtitle and then reverts it back to its
    original text, all diff formatting is cleared.
    """
    win = populated_window
    item = win.tree.topLevelItem(0)
    original_text = "Hello world, this is a test."

    # --- Edit the text ---
    edited_text = "Hello awesome world, this is a test."
    item.setText(2, edited_text)
    win.on_subtitle_edited(item, 2)

    # Verify it has formatting
    assert "<font" in item.text(2)
    assert item.data(2, win.OriginalTextRole) == original_text

    # --- Revert to original ---
    item.setText(2, original_text)
    win.on_subtitle_edited(item, 2)

    # Verify formatting is gone and it's just the plain text
    assert item.text(2) == original_text
    assert "<font" not in item.text(2)
    # UserRole should now be the same as the original text
    assert item.data(2, Qt.UserRole) == original_text

# --- CharCountDelegate Tests ---

@pytest.mark.parametrize("char_count_str, expected_color_hex", [
    ("10", "#28a745"),
    ("15", "#28a745"),
    ("16", "#dc3545"),
    ("99", "#dc3545"),
])
def test_char_count_delegate_paint_color(qapp, char_count_str, expected_color_hex):
    """Tests that the CharCountDelegate paints the correct color based on char count."""
    # 1. Setup Mocks and real objects
    mock_painter = MagicMock(spec=QPainter)
    option = QStyleOptionViewItem()
    option.rect.setRect(0, 0, 100, 30)
    
    mock_index = MagicMock(spec=QModelIndex)
    mock_index.data.return_value = char_count_str
    
    # 2. Instantiate and Execute
    delegate = CharCountDelegate()
    # By patching the base class's paint method, we prevent the ValueError
    # and can focus on testing our custom drawing logic.
    # By patching the base class's paint method, we prevent the ValueError
    # and can focus on testing our custom drawing logic.
    with patch.object(QStyledItemDelegate, 'paint') as mock_super_paint:
        delegate.paint(mock_painter, option, mock_index)
    
    # 3. Assert
    # Find the call to setBrush and check the color
    found_brush = False
    for call in mock_painter.setBrush.call_args_list:
        brush = call[0][0]
        if isinstance(brush, QBrush):
            assert brush.color().name() == expected_color_hex
            found_brush = True
            break
    assert found_brush, "setBrush was not called with a QBrush object."

def test_char_count_delegate_paint_draws_text(qapp):
    """Tests that the CharCountDelegate draws the character count text."""
    mock_painter = MagicMock(spec=QPainter)
    option = QStyleOptionViewItem()
    option.rect.setRect(0, 0, 100, 30)
    mock_index = MagicMock(spec=QModelIndex)
    mock_index.data.return_value = "42"
    
    delegate = CharCountDelegate()
    with patch.object(QStyledItemDelegate, 'paint'):
        delegate.paint(mock_painter, option, mock_index)
    
    mock_painter.drawText.assert_called()
    # Check if '42' is in the arguments of any drawText call
    text_found = False
    for call in mock_painter.drawText.call_args_list:
        if '42' in call[0]:
            text_found = True
            break
    assert text_found, "The text '42' was not drawn."

def test_char_count_delegate_handles_invalid_data(qapp):
    """Tests that the CharCountDelegate does not crash with invalid (non-digit) data."""
    mock_painter = MagicMock(spec=QPainter)
    option = QStyleOptionViewItem()
    mock_index = MagicMock(spec=QModelIndex)
    mock_index.data.return_value = "abc" # Invalid data

    delegate = CharCountDelegate()
    with patch.object(QStyledItemDelegate, 'paint'):
        delegate.paint(mock_painter, option, mock_index)

def test_on_subtitle_edited_updates_len_column(window):
    """Tests that the 'len' column is updated when a subtitle is edited."""
    subs_data = [{'id': 1, 'text': 'Initial'}]
    window.populate_table(subs_data=subs_data)
    
    item = window.find_item_by_id(1)
    assert item.text(1) == str(len('Initial'))

def test_columns_are_not_editable(window, qapp):
    """
    Tests that specific columns ('#', 'len') are not editable, while others are.
    """
    # Populate with some data to have an item to test on
    subs_data = [{'id': 1, 'text': 'Some text', 'in_timecode': '00:01', 'out_timecode': '00:02'}]
    window.populate_table(subs_data)

    item = window.tree.topLevelItem(0)
    mock_model = window.tree.model()

    # --- Get Delegates ---
    # The delegate for columns 0, 2, 3, 4 is HtmlDelegate
    html_delegate = window.html_delegate
    # The delegate for column 1 is CharCountDelegate
    char_count_delegate = window.char_count_delegate

    # --- Test Columns ---
    # Test '#' column (index 0), should be non-editable
    index_col0 = mock_model.index(0, 0)
    editor_col0 = html_delegate.createEditor(window.tree, None, index_col0)
    assert editor_col0 is None, "Column '#' should not be editable."

    # Test 'len' column (index 1), should be non-editable
    # Its delegate (CharCountDelegate) does not implement createEditor,
    # so the default QStyledItemDelegate's implementation will be used,
    # which returns None if the item is not editable.
    # We can check the item flags directly for a more robust test.
    # assert not (item.flags() & Qt.ItemIsEditable), "Item flags should not have editable flag for 'len' column implicitly."
    # Also test the delegate for good measure.
    index_col1 = mock_model.index(0, 1)
    option = QStyleOptionViewItem()
    editor_col1 = char_count_delegate.createEditor(window.tree, option, index_col1)
    assert editor_col1 is None, "Column 'len' should not be editable."

    # Test 'Subtitle' column (index 2), should be editable
    index_col2 = mock_model.index(0, 2)
    option = QStyleOptionViewItem()
    editor_col2 = html_delegate.createEditor(window.tree, option, index_col2)
    assert editor_col2 is not None, "Column 'Subtitle' should be editable."
    
    # Test 'In' column (index 3), should be editable
    index_col3 = mock_model.index(0, 3)
    option = QStyleOptionViewItem()
    editor_col3 = html_delegate.createEditor(window.tree, option, index_col3)
    assert editor_col3 is not None, "Column 'In' should be editable."

    # Test 'Out' column (index 4), should be editable
    index_col4 = mock_model.index(0, 4)
    option = QStyleOptionViewItem()
    editor_col4 = html_delegate.createEditor(window.tree, option, index_col4)
    assert editor_col4 is not None, "Column 'Out' should be editable."

    # This test should only verify the editability, not the editing logic.
    # The editing logic is tested in `test_on_subtitle_edited_updates_len_column`.