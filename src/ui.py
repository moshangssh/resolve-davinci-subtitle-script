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
    QFileDialog,
)
from PySide6.QtCore import Qt
import re
from src.resolve_integration import ResolveIntegration

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
    def __init__(self, resolve_integration: ResolveIntegration, parent=None):
        super().__init__(parent)
        self.resolve_integration = resolve_integration
        self.setWindowTitle("xdd sub")
        self.setGeometry(100, 100, 380, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_widgets()
        self._setup_layouts()
        self.search_text.textChanged.connect(self.filter_tree)
        self.export_button.clicked.connect(self.export_subtitles)

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
        self.export_button = QPushButton("导出")
        self.export_reimport_button = QPushButton("导出并重导入")

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
        bottom_layout.addWidget(self.export_button)
        bottom_layout.addWidget(self.export_reimport_button)
        self.main_layout.addLayout(bottom_layout)

    def populate_table(self, subs_data=None, json_path=None, hide=False):
        self.tree.clear()
        
        if json_path:
            subs_data = self.load_subtitles_from_json(json_path)

        if not subs_data:
            return

        for sub in subs_data:
            item = NumericTreeWidgetItem(self.tree)
            item.setText(0, str(sub.get('index', sub.get('id', ''))))
            item.setText(1, sub.get('text', ''))
            item.setText(2, sub.get('start', sub.get('in_timecode', '')))
            item.setText(3, sub.get('end', sub.get('out_timecode', '')))
            # The original 'in_frame' is not in the JSON, so we may need to adjust
            # how we handle jumping to timecode if that's still a feature.
            # For now, let's store something, or leave it empty.
            # If the original object is needed, the design must be reconsidered.
            item.setText(4, str(sub.get('in_frame', ''))) # Keep for now for compatibility
            if hide:
                item.setHidden(True)
        self.tree.sortItems(0, Qt.AscendingOrder)

    def load_subtitles_from_json(self, file_path):
        import json
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading subtitles from JSON: {e}")
            return []

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
                try:
                    # Escape special characters except for our wildcard '*'
                    # which we replace with '.*'
                    regex_pattern = '^' + '.*'.join(re.escape(part) for part in filter_text.split('*')) + '$'
                    matches = re.search(regex_pattern, subtitle_text) is not None
                except ImportError:
                    # Fallback if re is not available (unlikely)
                    matches = True # Or some other safe default

            item.setHidden(not matches)

    def export_subtitles(self):
        srt_content = self.resolve_integration.export_subtitles_to_srt()
        if not srt_content:
            # Optionally, show a message to the user that there's nothing to export
            print("No subtitles to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Subtitles",
            "",
            "SRT Files (*.srt);;All Files (*)",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(srt_content)
                print(f"Subtitles successfully exported to {file_path}")
            except IOError as e:
                print(f"Error writing to file: {e}")