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
    QHeaderView,
    QTabWidget,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextDocument, QFont, QPalette, QColor
import re
import difflib
import os
from .resolve_integration import ResolveIntegration


STYLE_SHEET = """
/* 仿 ChatGPT 官网主题 v1.0.0 */
/* 作者：https://linux.do/u/nianbroken/ */
/* Converted to QSS for PySide6 */

/* 全局样式 */
QMainWindow, QWidget {
    background-color: #f9f9f9; /* --color-background */
    color: #0d0d0d; /* --color-primary */
    font-family: "苹方-简", "Inter", "Roboto", "Source Han Sans", sans-serif;
    font-size: 10pt;
}

/* 检查器面板 */
#inspectorPanel {
    background-color: #ffffff; /* --chat-background */
    border: 1px solid #c2c2c2;
    border-radius: 12px;
}

/* 树状组件 (字幕列表) */
QTreeWidget {
    background-color: #ffffff; /* --chat-background */
    border: 1px solid #eaeaea; /* --color-background-soft */
    border-radius: 12px;
    color: #383a42;
}

QHeaderView::section {
    background-color: #f9f9f9; /* --navbar-background */
    color: #0d0d0d;
    padding: 4px;
    border: none;
    border-bottom: 1px solid #eaeaea;
}

QTreeWidget::item {
    padding: 8px;
    border-radius: 1.5rem; /* from .bubble .message-content-container */
}

QTreeWidget::item:selected, QTreeWidget::item:selected:alternate {
    background-color: #3266d0;
    color: #ffffff;
}

QTreeWidget::item:alternate {
    background-color: #f4f4f4; /* --chat-background-user */
}

/* 选项卡样式 */
QTabWidget::pane {
    border-top: 1px solid #eaeaea;
}

QTabBar::tab {
    background: #f9f9f9;
    border: 1px solid #eaeaea;
    border-bottom-color: #f9f9f9; /* same as pane color */
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 8ex;
    padding: 8px;
}

QTabBar::tab:selected, QTabBar::tab:hover {
    background: #ffffff;
}

QTabBar::tab:!selected {
    margin-top: 2px; /* make non-selected tabs look smaller */
}

/* 输入框和下拉框 */
QLineEdit, QComboBox {
    background-color: #f9f9f9;
    border: 1px solid #c2c2c2;
    border-radius: 8px;
    padding: 8px;
    color: #383a42;
    font-family: "JetBrainsMono Nerd Font Mono", "苹方-简", monospace;
}

QLineEdit:focus, QComboBox:focus, QLineEdit:hover, QComboBox:hover {
    border: 1px solid #3266d0;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 1px;
    border-left-color: #c2c2c2;
    border-left-style: solid;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}

QComboBox::down-arrow {
    image: url(arrow_down.svg);
    width: 12px;
    height: 12px;
}

QComboBox::down-arrow:on {
    image: url(arrow_up.svg);
}

/* 按钮 */
QPushButton {
    background-color: #f4f4f4; /* --chat-background-user */
    color: #0d0d0d;
    border: 1px solid #c2c2c2;
    border-radius: 8px;
    padding: 8px 16px;
}

QPushButton:hover {
    background-color: #eaeaea; /* --color-background-soft */
}

QPushButton:pressed {
    background-color: #3266d0;
    color: #ffffff;
    border-color: #3266d0;
}

/* 标签 */
QLabel {
    color: #5d5d5d;
}

/* 滚动条 */
QScrollBar:vertical {
    border: none;
    background: #f9f9f9;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #c2c2c2;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #f9f9f9;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #c2c2c2;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

class HtmlDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HtmlDelegate, self).__init__(parent)
        self.doc = QTextDocument(self)

    def createEditor(self, parent, option, index):
        # Only create an editor for columns that should be editable.
        if index.column() in [1, 2, 3]: # Subtitle, In, Out
            editor = super().createEditor(parent, option, index)
            if isinstance(editor, QLineEdit):
                editor.setFrame(False)
                palette = editor.palette()
                palette.setColor(QPalette.Base, Qt.transparent)
                palette.setColor(QPalette.Text, QColor("#0d0d0d"))
                editor.setPalette(palette)
                editor.setStyleSheet("padding: 0px; border: 0px;")
            return editor
        else:
            # For non-editable columns (like '#'), return None to prevent editing.
            return None

    def paint(self, painter, option, index):
        options = option
        self.initStyleOption(options, index)

        # Force a uniform selection color, overriding any alternate row color
        if options.state & QStyle.State_Selected:
            options.palette.setColor(QPalette.Highlight, QColor("#3266d0"))
            options.palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

        painter.save()

        # We must draw the background and selection effects before anything else.
        # To prevent the default delegate from drawing the text, we clear it.
        original_text = options.text
        options.text = ""
        style = options.widget.style()
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        # A more robust check for the editing state, directly querying the view.
        # This is the definitive fix for the overlapping text issue.
        view = self.parent()
        is_editing = (view.state() == QAbstractItemView.EditingState) and (view.currentIndex() == index)

        if not is_editing:
            # Restore the original text to render it via QTextDocument
            self.doc.setHtml(original_text)

            # Get the rectangle for the text and draw the HTML document inside it.
            textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)

            # --- Start of Vertical Centering Logic ---
            # Set the available width for the document to calculate its height correctly.
            self.doc.setTextWidth(textRect.width())
            textHeight = self.doc.size().height()

            # Calculate the vertical offset to center the text.
            offsetY = (textRect.height() - textHeight) / 2.0

            # Translate the painter to the new starting point, including the offset.
            painter.translate(textRect.x(), textRect.y() + offsetY)
            
            # Clip the painter to the actual text area to prevent drawing outside bounds.
            painter.setClipRect(0, 0, textRect.width(), textHeight)
            
            self.doc.drawContents(painter)
            # --- End of Vertical Centering Logic ---

        painter.restore()

    def setEditorData(self, editor, index):
        # When editing starts, always provide the clean, non-HTML text.
        # We store the current clean text in the UserRole.
        text = index.model().data(index, Qt.UserRole)
        if text is None:
            # Fallback for items that haven't been modified yet
            text = index.model().data(index, Qt.DisplayRole)
            text = re.sub(r'<[^>]+>', '', text)
        editor.setText(text)

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
    OriginalTextRole = Qt.UserRole + 1
    # Signal emitted when a subtitle's clean text data has been changed by the user.
    # Arguments: item_index (int), new_clean_text (str)
    subtitleDataChanged = Signal(int, str)

    def __init__(self, resolve_integration: ResolveIntegration, parent=None):
        super().__init__(parent)
        self.resolve_integration = resolve_integration
        self.setWindowTitle("Subvigator - DaVinci Resolve Subtitle Editor")
        self.setGeometry(100, 100, 1200, 800) # Increased default size

        # --- Dynamic Stylesheet Injection ---
        # Get the absolute path to the directory containing this script (ui.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Construct absolute paths for the SVG icons
        arrow_down_path = os.path.join(script_dir, "arrow_down.svg").replace("\\", "/")
        arrow_up_path = os.path.join(script_dir, "arrow_up.svg").replace("\\", "/")
        
        # Inject the absolute paths into the stylesheet
        dynamic_style_sheet = STYLE_SHEET.replace(
            "url(arrow_down.svg)", f"url({arrow_down_path})"
        ).replace(
            "url(arrow_up.svg)", f"url({arrow_up_path})"
        )

        # Apply global font and stylesheet
        font = QFont("Inter", 10)
        self.setFont(font)
        self.setStyleSheet(dynamic_style_sheet)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout is now horizontal
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(8)

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
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(['#', 'Subtitle', 'In', 'Out', 'StartFrame'])
        self.tree.setColumnHidden(4, True) # StartFrame is data-only

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.html_delegate = HtmlDelegate(self.tree)
        self.tree.setItemDelegate(self.html_delegate)

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

        # Tab Widget for inspector
        self.inspector_tabs = QTabWidget()

    def _setup_layouts(self):
        # --- Right Panel (Inspector) ---
        inspector_panel = QWidget()
        inspector_panel.setObjectName("inspectorPanel") # For styling
        inspector_layout = QVBoxLayout(inspector_panel)
        inspector_layout.setContentsMargins(10, 10, 10, 10)
        inspector_layout.setSpacing(8)

        # --- Filter Tab ---
        filter_tab = QWidget()
        filter_layout = QVBoxLayout(filter_tab)
        filter_layout.setContentsMargins(0, 10, 0, 0)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_text)
        filter_layout.addLayout(search_layout)
        filter_layout.addWidget(self.search_type_combo)
        filter_layout.addStretch()

        # --- Find/Replace Tab ---
        find_replace_tab = QWidget()
        find_replace_layout = QVBoxLayout(find_replace_tab)
        find_replace_layout.setContentsMargins(0, 10, 0, 0)

        find_replace_layout.addWidget(self.find_label)
        find_replace_layout.addWidget(self.find_text)
        find_replace_layout.addWidget(self.replace_label)
        find_replace_layout.addWidget(self.replace_text)
        
        find_replace_buttons_layout = QHBoxLayout()
        find_replace_buttons_layout.addWidget(self.find_next_button)
        find_replace_buttons_layout.addWidget(self.replace_button)
        find_replace_buttons_layout.addWidget(self.replace_all_button)
        
        find_replace_layout.addLayout(find_replace_buttons_layout)
        find_replace_layout.addStretch()

        # Add tabs to the tab widget
        self.inspector_tabs.addTab(filter_tab, "Filter")
        self.inspector_tabs.addTab(find_replace_tab, "Find & Replace")

        inspector_layout.addWidget(self.inspector_tabs)

        # Bottom controls
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.track_combo)
        bottom_layout.addWidget(self.refresh_button)
        inspector_layout.addLayout(bottom_layout)
        inspector_layout.addWidget(self.export_reimport_button)

        # --- Main Layout ---
        # Left side: Tree Widget
        self.main_layout.addWidget(self.tree, 2) # 2/3 of the space

        # Right side: Inspector Panel
        self.main_layout.addWidget(inspector_panel, 1) # 1/3 of the space


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
            item.setData(1, self.OriginalTextRole, text) # Ensure original text is stored from the start
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
        
        # Prioritize the 'pre-replace' original text if it exists
        original_text = item.data(1, self.OriginalTextRole)
        
        # Fallback to the regular UserRole text if no 'pre-replace' text is found
        if original_text is None:
            original_text = item.data(1, Qt.UserRole)

        if original_text is None:
            original_text = ""
        
        if clean_new_text == original_text:
            # If the text is reverted to the original, clear the special role and formatting
            self.tree.blockSignals(True)
            item.setData(1, self.OriginalTextRole, None)
            item.setText(1, original_text)
            item.setData(1, Qt.UserRole, original_text) # Also reset UserRole
            self.tree.blockSignals(False)
            return

        # When a user edits, we want to show the diff against the true original text.
        # The style should reflect a "replace" operation, similar to find/replace,
        # to maintain a consistent history of changes.
        style_config = {
            'delete': '<font color="red"><s>{text}</s></font>',
            'replace': '<font color="blue">{text}</font>',
            'insert': '<font color="blue">{text}</font>',
        }
        
        html_text = self._generate_diff_html(original_text, clean_new_text, style_config)

        self.tree.blockSignals(True)
        item.setText(1, html_text)
        # Update the UserRole to store the new, clean text. This is the source of truth for the data model.
        item.setData(1, Qt.UserRole, clean_new_text)
        # The OriginalTextRole should NOT be updated here. It must always hold the initial text.
        self.tree.blockSignals(False)

        # Emit a signal with the clean data for the controller to handle saving.
        try:
            item_index = int(item.text(0))
            self.subtitleDataChanged.emit(item_index, clean_new_text)
        except (ValueError, TypeError):
            # Handle cases where the item index is not a valid number
            # Handle cases where the item index is not a valid number
            # For now, we just suppress the error. A more robust solution might log this.
            pass

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
        
        # If this is the first replacement, store the original text
        if item.data(1, self.OriginalTextRole) is None:
            item.setData(1, self.OriginalTextRole, original_text)

        # The original_text for the diff should be the one from OriginalTextRole if available
        base_text = item.data(1, self.OriginalTextRole) or original_text

        diff_html = self._generate_diff_html(base_text, new_text, {
             'delete': '<font color="red"><s>{text}</s></font>',
             'replace': '<font color="blue">{text}</font>',
             'insert': '<font color="blue">{text}</font>',
        })

        self.tree.blockSignals(True)
        item.setText(1, diff_html)
        item.setData(1, Qt.UserRole, new_text) # Update the user role with the new clean text
        # DO NOT update OriginalTextRole here. It's set once and preserved.
        self.tree.blockSignals(False)

    def get_all_subtitles_data(self):
        """
        Retrieves all subtitle entries from the tree as a list of dictionaries,
        ensuring the text is the clean, underlying data, not the display HTML.
        """
        subs_data = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            
            # Prioritize UserRole for the most up-to-date clean text
            clean_text = item.data(1, Qt.UserRole)
            
            # If UserRole is not set (e.g., for unmodified items), get the display text and clean it
            if clean_text is None:
                clean_text = re.sub(r'<[^>]+>', '', item.text(1))

            try:
                index = int(item.text(0))
            except (ValueError, TypeError):
                index = -1 # Or some other default

            try:
                start_frame = int(item.text(4))
            except (ValueError, TypeError):
                start_frame = -1 # Or some other default

            subs_data.append({
                'id': index,
                'index': index,
                'text': clean_text,
                'start': item.text(2),
                'end': item.text(3),
                'in_frame': start_frame,
            })
        return subs_data
        self.tree.setCurrentItem(item)


    def update_all_items_for_replace(self, changes):
        """Updates all changed items with diff highlighting."""
        self.tree.blockSignals(True)
        for change in changes:
            item = self.find_item_by_id(change['index'])
            if item:
                # If this is the first replacement for this item, store its original text
                if item.data(1, self.OriginalTextRole) is None:
                    item.setData(1, self.OriginalTextRole, change['old'])
                
                # The original_text for the diff should be the one from OriginalTextRole if available
                base_text = item.data(1, self.OriginalTextRole) or change['old']

                diff_html = self._generate_diff_html(base_text, change['new'], {
                    'delete': '<font color="red"><s>{text}</s></font>',
                    'replace': '<font color="blue">{text}</font>',
                    'insert': '<font color="blue">{text}</font>',
                })
                item.setText(1, diff_html)
                item.setData(1, Qt.UserRole, change['new'])
                # DO NOT update OriginalTextRole here. It's set once and preserved.

        self.tree.blockSignals(False)
