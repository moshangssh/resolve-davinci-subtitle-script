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
    QTreeWidgetItemIterator,
)
from PySide6.QtCore import Qt
import re
from src.resolve_integration import ResolveIntegration

class NumericTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        if not isinstance(other, QTreeWidgetItem):
            return NotImplemented
        try:
            return int(self.text(0)) < int(other.text(0))
        except (ValueError, TypeError):
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
        self.search_text.textChanged.connect(self.on_search_text_changed)
        self.find_text.textChanged.connect(self.on_find_text_changed)
        self.find_next_button.clicked.connect(self.find_next)
        self.replace_button.clicked.connect(self.replace_current)
        self.replace_all_button.clicked.connect(self.replace_all)

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
        self.export_reimport_button = QPushButton("导出并重导入")

        # Find and Replace widgets
        self.find_label = QLabel("Find:")
        self.find_text = QLineEdit()
        self.find_text.setPlaceholderText("Find Text")
        self.replace_label = QLabel("Replace:")
        self.replace_text = QLineEdit()
        self.replace_text.setPlaceholderText("Replace With")
        self.find_next_button = QPushButton("Find Next")
        self.replace_button = QPushButton("Replace")
        self.replace_all_button = QPushButton("Replace All")

    def _setup_layouts(self):
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_text)
        search_layout.addWidget(self.search_type_combo)
        self.main_layout.addLayout(search_layout)

        find_replace_layout = QHBoxLayout()
        find_replace_layout.addWidget(self.find_label)
        find_replace_layout.addWidget(self.find_text)
        find_replace_layout.addWidget(self.replace_label)
        find_replace_layout.addWidget(self.replace_text)
        self.main_layout.addLayout(find_replace_layout)

        find_replace_buttons_layout = QHBoxLayout()
        find_replace_buttons_layout.addWidget(self.find_next_button)
        find_replace_buttons_layout.addWidget(self.replace_button)
        find_replace_buttons_layout.addWidget(self.replace_all_button)
        self.main_layout.addLayout(find_replace_buttons_layout)


        self.main_layout.addWidget(self.tree)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.track_combo)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.refresh_button)
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
            item.setFlags(item.flags() | Qt.ItemIsEditable)
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

    def export_subtitles(self):
        if not hasattr(self, 'subtitles_data') or not self.subtitles_data:
            print("No subtitle data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Subtitles", "", "JSON (*.json)")

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(self.subtitles_data, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            print(f"Failed to export subtitles: {e}")

    def on_search_text_changed(self):
        self.filter_tree(self.search_text.text())

    def on_find_text_changed(self):
        self.filter_tree(self.find_text.text())

    def filter_tree(self, filter_text):
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

    def find_next(self):
        find_text = self.find_text.text()
        if not find_text:
            return

        start_item = self.tree.currentItem()

        item_iterator = QTreeWidgetItemIterator(self.tree, QTreeWidgetItemIterator.All)
        
        # If a start_item is selected, move the iterator to it before starting the search.
        if start_item:
            while item_iterator.value():
                if item_iterator.value() == start_item:
                    # Move to the next item to start the search from there
                    item_iterator += 1
                    break
                item_iterator += 1
        
        # Start search from the current iterator position

        while item_iterator.value():
            item = item_iterator.value()
            if find_text in item.text(1):
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                return
            item_iterator += 1
        
        # If we reached the end, wrap around and search from the beginning
        item_iterator = QTreeWidgetItemIterator(self.tree, QTreeWidgetItemIterator.All)
        while item_iterator.value() and item_iterator.value() != start_item:
            item = item_iterator.value()
            if find_text in item.text(1):
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                return
            item_iterator += 1
        # Check the start item itself if we've wrapped
        if start_item and find_text in start_item.text(1) and self.tree.currentItem() != start_item:
             self.tree.setCurrentItem(start_item)
             self.tree.scrollToItem(start_item)


    def replace_current(self):
        find_text = self.find_text.text()
        replace_text = self.replace_text.text()
        if not find_text:
            return

        selected_item = self.tree.currentItem()
        if selected_item and find_text in selected_item.text(1):
            current_text = selected_item.text(1)
            new_text = current_text.replace(find_text, replace_text, 1) # Replace only the first occurrence
            selected_item.setText(1, new_text)
        self.find_next() # Move to the next match

    def replace_all(self):
        find_text = self.find_text.text()
        replace_text = self.replace_text.text()
        if not find_text:
            return

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if find_text in item.text(1):
                new_text = item.text(1).replace(find_text, replace_text)
                item.setText(1, new_text)
