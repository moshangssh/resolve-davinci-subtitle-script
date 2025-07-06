import pytest
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from unittest.mock import Mock
from ui import NumericTreeWidgetItem, SubvigatorWindow

# Fixture to provide a QApplication instance
@pytest.fixture(scope="session")
def app():
    """
    Creates a QApplication instance for the test session.
    """
    q_app = QApplication.instance()
    if not q_app:
        q_app = QApplication([])
    return q_app

# Tests for NumericTreeWidgetItem
@pytest.mark.parametrize("text1, text2, expected", [
    ("10", "2", False),      # Numeric comparison
    ("2", "10", True),       # Numeric comparison
    ("1", "1", False),       # Numeric comparison
    ("a", "b", True),        # String fallback
    ("b", "a", False),       # String fallback
    ("1", "a", True),        # String fallback
    ("a", "1", False),       # String fallback
])
def test_numeric_tree_widget_item_lt(text1, text2, expected):
    """
    Tests the custom less-than comparison of NumericTreeWidgetItem.
    """
    item1 = NumericTreeWidgetItem()
    item1.setText(0, text1)
    item2 = QTreeWidgetItem() # Compare against a standard item
    item2.setText(0, text2)
    
    assert (item1 < item2) == expected

def test_numeric_tree_widget_item_lt_invalid_type(app):
    """
    Tests that the comparison falls back gracefully with an incompatible type.
    """
    item1 = NumericTreeWidgetItem()
    item1.setText(0, "10")
    item2 = "not_a_widget"
    
    # Comparing with a non-QTreeWidgetItem should result in a TypeError
    # because of the NotImplemented return value.
    with pytest.raises(TypeError):
        item1 < item2


# Tests for SubvigatorWindow
@pytest.fixture
def window(app):
    """
    Creates an instance of SubvigatorWindow for testing.
    """
    win = SubvigatorWindow()
    return win

def test_subvigator_window_init(window):
    """
    Tests the initialization of the SubvigatorWindow.
    """
    assert window.windowTitle() == "Andy's Subvigator (Python Port)"
    assert window.geometry().width() == 380
    assert window.geometry().height() == 700
    assert window.central_widget is not None
    assert window.main_layout is not None
    assert window.search_text.placeholderText() == "Search Text Filter"
    assert window.search_type_combo.count() == 5
    assert window.tree.columnCount() == 3
    header = window.tree.headerItem()
    assert header.text(0) == '#'
    assert header.text(1) == 'Subtitle'
    assert header.text(2) == 'StartFrame'
    assert window.tree.isColumnHidden(2) == True

def test_populate_table(window):
    """
    Tests the populate_table method of SubvigatorWindow.
    """
    # Create mock subtitle objects
    sub1 = Mock()
    sub1.GetName.return_value = "Hello"
    sub1.GetStart.return_value = 1000
    
    sub2 = Mock()
    sub2.GetName.return_value = "World"
    sub2.GetStart.return_value = 2000

    subs_data = {1: sub1, 2: sub2}
    
    window.populate_table(subs_data)
    
    assert window.tree.topLevelItemCount() == 2
    
    # Check item 1
    item1 = window.tree.topLevelItem(0)
    assert item1.text(0) == "1"
    assert item1.text(1) == "Hello"
    assert item1.text(2) == "1000"
    assert item1.isHidden() == False
    
    # Check item 2
    item2 = window.tree.topLevelItem(1)
    assert item2.text(0) == "2"
    assert item2.text(1) == "World"
    assert item2.text(2) == "2000"
    assert item2.isHidden() == False

def test_populate_table_with_hide(window):
    """
    Tests the populate_table method with the 'hide' parameter set to True.
    """
    sub1 = Mock()
    sub1.GetName.return_value = "Hidden Sub"
    sub1.GetStart.return_value = 3000
    
    subs_data = {1: sub1}
    
    window.populate_table(subs_data, hide=True)
    
    assert window.tree.topLevelItemCount() == 1
    item = window.tree.topLevelItem(0)
    assert item.isHidden() == True

def test_populate_table_clears_previous_data(window):
    """
    Tests that populate_table clears existing items before adding new ones.
    """
    # First population
    sub1 = Mock()
    sub1.GetName.return_value = "First"
    sub1.GetStart.return_value = 100
    window.populate_table({1: sub1})
    assert window.tree.topLevelItemCount() == 1
    
    # Second population
    sub2 = Mock()
    sub2.GetName.return_value = "Second"
    sub2.GetStart.return_value = 200
    window.populate_table({2: sub2})
    assert window.tree.topLevelItemCount() == 1
    item = window.tree.topLevelItem(0)
    assert item.text(1) == "Second"

def test_table_sorting(window):
    """
    Tests if the table correctly sorts items numerically by the first column.
    """
    sub1 = Mock()
    sub1.GetName.return_value = "Sub 1"
    sub1.GetStart.return_value = 100
    
    sub10 = Mock()
    sub10.GetName.return_value = "Sub 10"
    sub10.GetStart.return_value = 1000
    
    sub2 = Mock()
    sub2.GetName.return_value = "Sub 2"
    sub2.GetStart.return_value = 200

    subs_data = {10: sub10, 1: sub1, 2: sub2}
    
    window.populate_table(subs_data)
    
    # Check the order after sorting
    assert window.tree.topLevelItem(0).text(0) == "1"
    assert window.tree.topLevelItem(1).text(0) == "2"
    assert window.tree.topLevelItem(2).text(0) == "10"