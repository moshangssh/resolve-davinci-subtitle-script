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
    QStyledItemDelegate,
    QStyle,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
import re
import difflib
from src.resolve_integration import ResolveIntegration

class HtmlDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HtmlDelegate, self).__init__(parent)
        self.doc = QTextDocument(self)

    def paint(self, painter, option, index):
        options = option
        self.initStyleOption(options, index)

        painter.save()

        self.doc.setHtml(options.text)

        # Remove the original text to avoid drawing it twice.
        options.text = ""
        # Draw the background and selection state.
        style = options.widget.style()
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        # Adjust the rectangle for drawing the document.
        # This is a basic adjustment; more complex scenarios might need more tuning.
        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        
        self.doc.drawContents(painter)

        painter.restore()

    def setEditorData(self, editor, index):
        # When editing starts, provide the plain text (from UserRole if available, otherwise from DisplayRole)
        # and ensure it's clean of HTML.
        text = index.model().data(index, Qt.DisplayRole)
        clean_text = re.sub(r'<[^>]+>', '', text)
        editor.setText(clean_text)

    def setModelData(self, editor, model, index):
        # When editing finishes, get the plain text from the editor
        # and set it as the item's text. This will trigger itemChanged.
        model.setData(index, editor.text(), Qt.EditRole)

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
        self.tree.itemChanged.connect(self.on_subtitle_edited)

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
        self.html_delegate = HtmlDelegate(self.tree)
        self.tree.setItemDelegateForColumn(1, self.html_delegate)

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
        self.tree.blockSignals(True)
        self.tree.clear()
        
        if json_path:
            subs_data = self.load_subtitles_from_json(json_path)

        if not subs_data:
            self.tree.blockSignals(False)
            return

        for sub in subs_data:
            item = NumericTreeWidgetItem(self.tree)
            item.setText(0, str(sub.get('index', sub.get('id', ''))))
            item.setText(1, sub.get('text', ''))
            item.setData(1, Qt.UserRole, sub.get('text', ''))
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
        self.tree.blockSignals(False)

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
        if selected_item:
            original_text = selected_item.data(1, Qt.UserRole)
            if find_text in original_text:
                # Manually construct HTML for predictable highlighting
                delete_html = f'<font color="red"><s>{find_text}</s></font>'
                insert_html = f'<font color="blue">{replace_text}</font>'
                # Use html.escape for the parts we are not styling
                import html
                escaped_original = html.escape(original_text)
                escaped_find = html.escape(find_text)

                # This is a simplified approach. A more robust solution would handle multiple occurrences.
                html_text = escaped_original.replace(escaped_find, delete_html + insert_html, 1)

                self.tree.blockSignals(True)
                selected_item.setText(1, html_text)
                self.tree.blockSignals(False)
        self.find_next()

    def replace_all(self):
        find_text = self.find_text.text()
        replace_text = self.replace_text.text()
        if not find_text:
            return

        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            original_text = item.data(1, Qt.UserRole)
            if find_text in original_text:
                # Manually construct HTML for predictable highlighting
                delete_html = f'<font color="red"><s>{find_text}</s></font>'
                insert_html = f'<font color="blue">{replace_text}</font>'
                import html
                escaped_original = html.escape(original_text)
                escaped_find = html.escape(find_text)
                
                html_text = escaped_original.replace(escaped_find, delete_html + insert_html)
                item.setText(1, html_text)
        self.tree.blockSignals(False)

    def _generate_diff_html(self, original_text, new_text, style_config):
        html_text = ""
        s = difflib.SequenceMatcher(None, original_text, new_text)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == 'equal':
                html_text += new_text[j1:j2]
            elif tag == 'replace':
                html_text += style_config['delete'].format(text=original_text[i1:i2])
                html_text += style_config['replace'].format(text=new_text[j1:j2])
            elif tag == 'delete':
                html_text += style_config['delete'].format(text=original_text[i1:i2])
            elif tag == 'insert':
                html_text += style_config['insert'].format(text=new_text[j1:j2])
        return html_text

    def on_subtitle_edited(self, item, column):
        if column != 1:
            return

        new_text = item.text(1)
        clean_new_text = re.sub(r'<[^>]+>', '', new_text)
        original_text = item.data(1, Qt.UserRole)

        if original_text is None:
            original_text = ""

        if clean_new_text == original_text:
            return
        
        style_config = {
            'replace': '<font color="green">{text}</font>',
            'insert': '<font color="green">{text}</font>',
            'delete': '' # No visible representation for deleted text in this case
        }
        
        html_text = self._generate_diff_html(original_text, clean_new_text, style_config)

        self.tree.blockSignals(True)
        item.setText(1, html_text)
        self.tree.blockSignals(False)
