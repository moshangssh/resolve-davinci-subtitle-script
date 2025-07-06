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
        self.setWindowTitle("Andy's Subvigator (Python Port)")
        self.setGeometry(100, 100, 380, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_widgets()
        self._setup_layouts()

    def _create_widgets(self):
        self.search_label = QLabel("Filter:")
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Search Text Filter")
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(['Contains', 'Exact', 'Starts With', 'Ends With', 'Wildcard'])

        self.dynamic_search_checkbox = QCheckBox("Dynamic search text")
        self.drop_frame_checkbox = QCheckBox("DF navigation")

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['#', 'Subtitle', 'StartFrame'])
        self.tree.setColumnWidth(0, 58)
        self.tree.setColumnWidth(1, 280)
        self.tree.setColumnHidden(2, True)

        self.track_combo = QComboBox()
        self.combine_subs_label = QLabel("Combine Subs:")
        self.combine_subs_combo = QComboBox()
        self.combine_subs_combo.addItems([str(i) for i in range(1, 11)])
        self.refresh_button = QPushButton("Refresh")

    def _setup_layouts(self):
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_text)
        search_layout.addWidget(self.search_type_combo)
        self.main_layout.addLayout(search_layout)

        options_layout = QHBoxLayout()
        options_layout.addWidget(self.dynamic_search_checkbox)
        options_layout.addWidget(self.drop_frame_checkbox)
        self.main_layout.addLayout(options_layout)

        self.main_layout.addWidget(self.tree)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.track_combo)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.combine_subs_label)
        bottom_layout.addWidget(self.combine_subs_combo)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.refresh_button)
        self.main_layout.addLayout(bottom_layout)

    def populate_table(self, subs_data, hide=False):
        self.tree.clear()
        for i, sub_obj in subs_data.items():
            item = NumericTreeWidgetItem(self.tree)
            item.setText(0, str(i))
            item.setText(1, sub_obj.GetName())
            item.setText(2, str(sub_obj.GetStart()))
            if hide:
                item.setHidden(True)
        self.tree.sortItems(0, Qt.AscendingOrder)