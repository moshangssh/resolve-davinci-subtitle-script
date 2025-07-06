# ui.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QCheckBox,
)
from PySide6.QtCore import Qt

class NumericTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        if not isinstance(other, QTreeWidgetItem):
            return NotImplemented

        try:
            # First, try to compare numerically
            return int(self.text(0)) < int(other.text(0))
        except (ValueError, TypeError):
            # If numerical comparison fails, fallback to string comparison
            return self.text(0) < other.text(0)

class SubvigatorWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("xdd sub")
        self.setGeometry(100, 100, 380, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_widgets()
        self._setup_layouts()
        self.search_text.textChanged.connect(self.filter_tree)

    def _create_widgets(self):
        self.search_label = QLabel("Filter:")
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Search Text Filter")
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(['Contains', 'Exact', 'Starts With', 'Ends With', 'Wildcard'])

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(['#', 'Subtitle', 'In', 'Out', 'StartFrame'])
        self.tree.setColumnWidth(0, 40)  # #
        self.tree.setColumnWidth(1, 180) # Subtitle
        self.tree.setColumnWidth(2, 80)  # In
        self.tree.setColumnWidth(3, 80)  # Out
        self.tree.setColumnHidden(4, True) # StartFrame

        self.track_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh")

    def _setup_layouts(self):
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_text)
        search_layout.addWidget(self.search_type_combo)
        self.main_layout.addLayout(search_layout)

        self.main_layout.addWidget(self.tree)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.track_combo)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.refresh_button)
        self.main_layout.addLayout(bottom_layout)

    def populate_table(self, subs_data, hide=False):
        self.tree.clear()
        for sub in subs_data:
            item = NumericTreeWidgetItem(self.tree)
            item.setText(0, str(sub['id']))
            item.setText(1, sub['text'])
            item.setText(2, sub['in_timecode'])
            item.setText(3, sub['out_timecode'])
            item.setText(4, str(sub['in_frame']))
            if hide:
                item.setHidden(True)
        self.tree.sortItems(0, Qt.AscendingOrder)

    def filter_tree(self):
        filter_text = self.search_text.text()
        filter_type = self.search_type_combo.currentText()
        root = self.tree.invisibleRootItem()

        for i in range(root.childCount()):
            item = root.child(i)
            subtitle_text = item.text(1) # Subtitle text is now in column 1
            
            matches = False
            if not filter_text:
                matches = True
            elif filter_type == 'Contains':
                matches = filter_text in subtitle_text
            elif filter_type == 'Exact':
                matches = filter_text == subtitle_text
            elif filter_type == 'Starts With':
                matches = subtitle_text.startswith(filter_text)
            elif filter_type == 'Ends With':
                matches = subtitle_text.endswith(filter_text)
            elif filter_type == 'Wildcard':
                # Basic wildcard support: * matches any sequence of characters
                # More complex patterns could be handled with regex
                parts = filter_text.split('*')
                if len(parts) == 1:
                    matches = filter_text in subtitle_text
                else:
                    try:
                        import re
                        # Escape special characters except for our wildcard '*'
                        # which we replace with '.*'
                        regex_pattern = '.*'.join(re.escape(part) for part in parts)
                        matches = re.search(regex_pattern, subtitle_text) is not None
                    except ImportError:
                        # Fallback if re is not available (unlikely)
                        matches = True # Or some other safe default

            item.setHidden(not matches)