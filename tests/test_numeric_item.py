import unittest
import sys
import os
from PySide6.QtWidgets import QApplication

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from subvigator_merged import NumericTreeWidgetItem

class TestNumericTreeWidgetItem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # A QApplication instance is required for creating widgets.
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_lt_numeric(self):
        """Test numeric comparison."""
        item1 = NumericTreeWidgetItem()
        item1.setText(0, "10")
        item2 = NumericTreeWidgetItem()
        item2.setText(0, "2")
        self.assertTrue(item2 < item1)
        self.assertFalse(item1 < item2)

    def test_lt_non_numeric(self):
        """Test fallback to string comparison for non-numeric text."""
        item1 = NumericTreeWidgetItem()
        item1.setText(0, "abc")
        item2 = NumericTreeWidgetItem()
        item2.setText(0, "def")
        # Falls back to standard string comparison
        self.assertTrue(item1 < item2)

    def test_lt_mixed_types(self):
        """Test fallback for mixed numeric and non-numeric text."""
        item1 = NumericTreeWidgetItem()
        item1.setText(0, "10")
        item2 = NumericTreeWidgetItem()
        item2.setText(0, "abc")
        # Falls back to default QTreeWidgetItem behavior (string comparison)
        self.assertFalse(item1 < item2) # '10' is not < 'abc'
        self.assertTrue(item2 < item1)  # 'abc' is < '10' in string comparison

if __name__ == '__main__':
    unittest.main()