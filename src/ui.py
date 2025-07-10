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
from resolve_integration import ResolveIntegration

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

    def populate_table(self, subs_data, hide=False):
        self.tree.blockSignals(True)
        self.tree.clear()

        if not subs_data:
            self.tree.blockSignals(False)
            return

        for sub in subs_data:
            item = NumericTreeWidgetItem(self.tree)
            item.setText(0, str(sub.get('index', sub.get('id', ''))))
            text = sub.get('text', '')
            item.setText(1, text)
            item.setData(1, Qt.UserRole, text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setText(2, sub.get('start', sub.get('in_timecode', '')))
            item.setText(3, sub.get('end', sub.get('out_timecode', '')))
            item.setText(4, str(sub.get('in_frame', '')))
            if hide:
                item.setHidden(True)
        self.tree.sortItems(0, Qt.AscendingOrder)
        self.tree.blockSignals(False)

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

    def find_item_by_id(self, item_id):
        """Finds a QTreeWidgetItem by its ID in the first column."""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.text(0) == str(item_id):
                return item
        return None

    def update_item_for_replace(self, item_index, original_text, new_text):
        """Updates a single item's text with diff highlighting."""
        item = self.find_item_by_id(item_index)
        if not item:
            return
        
        diff_html = self._generate_diff_html(original_text, new_text, {
             'delete': '<font color="red"><s>{text}</s></font>',
             'replace': '<font color="blue">{text}</font>',
             'insert': '<font color="blue">{text}</font>',
        })

        self.tree.blockSignals(True)
        item.setText(1, diff_html)
        item.setData(1, Qt.UserRole, new_text) # Update the user role with the new clean text
        self.tree.blockSignals(False)
        self.tree.setCurrentItem(item)


    def update_all_items_for_replace(self, changes):
        """Updates all changed items with diff highlighting."""
        self.tree.blockSignals(True)
        for change in changes:
            item = self.find_item_by_id(change['index'])
            if item:
                diff_html = self._generate_diff_html(change['old'], change['new'], {
                    'delete': '<font color="red"><s>{text}</s></font>',
                    'replace': '<font color="blue">{text}</font>',
                    'insert': '<font color="blue">{text}</font>',
                })
                item.setText(1, diff_html)
                item.setData(1, Qt.UserRole, change['new'])
        self.tree.blockSignals(False)
