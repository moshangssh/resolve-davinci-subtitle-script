# ui.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QTreeWidget,
    QHeaderView,
    QTreeWidgetItemIterator,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import re
import os
from .resolve_integration import ResolveIntegration
from .ui_components import CharCountDelegate, HtmlDelegate, NumericTreeWidgetItem
from .inspector_panel import InspectorPanel
from . import ui_logic
from .ui_model import UIModel


def load_stylesheet(script_dir):
    """Loads the stylesheet from an external file."""
    qss_path = os.path.join(script_dir, "style.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Stylesheet not found at {qss_path}")
        return ""

class SubvigatorWindow(QMainWindow):
    OriginalTextRole = Qt.UserRole + 1
    # Signal emitted when a subtitle's clean text data has been changed by the user.
    # Arguments: item_index (int), new_clean_text (str)
    subtitleDataChanged = Signal(int, str)

    def __init__(self, resolve_integration: ResolveIntegration, parent=None):
        super().__init__(parent)
        self.resolve_integration = resolve_integration
        self.setWindowTitle("xdd - 字幕编辑器")
        self.setGeometry(100, 100, 1200, 800) # Increased default size
        self.ui_model = UIModel()

        # --- Dynamic Stylesheet Injection ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        style_sheet = load_stylesheet(script_dir)
        arrow_down_path = os.path.join(script_dir, "arrow_down.svg").replace("\\", "/")
        arrow_up_path = os.path.join(script_dir, "arrow_up.svg").replace("\\", "/")
        dynamic_style_sheet = style_sheet.replace(
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
        self._connect_signals()

    def _create_widgets(self):
        self.tree = QTreeWidget()
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(['#', '长度', '字幕', '入点', '出点', '开始帧'])
        self.tree.setColumnHidden(5, True) # StartFrame is data-only

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # #
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # len
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Subtitle
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # In
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Out
        
        self.char_count_delegate = CharCountDelegate(self.tree)
        self.html_delegate = HtmlDelegate(self.tree)
        self.tree.setItemDelegateForColumn(1, self.char_count_delegate)
        self.tree.setItemDelegateForColumn(0, self.html_delegate) # Make '#' non-editable
        self.tree.setItemDelegateForColumn(2, self.html_delegate)
        self.tree.setItemDelegateForColumn(3, self.html_delegate) # Make 'In' editable
        self.tree.setItemDelegateForColumn(4, self.html_delegate) # Make 'Out' editable

        self.inspector = InspectorPanel()

    def _setup_layouts(self):
        # --- Main Layout ---
        # Left side: Tree Widget
        self.main_layout.addWidget(self.tree, 2) # 2/3 of the space

        # Right side: Inspector Panel
        self.main_layout.addWidget(self.inspector, 1) # 1/3 of the space

    def _connect_signals(self):
        # This will be connected in the ApplicationController
        # self.inspector.find_next_button.clicked.connect(self.find_next)
        self.tree.itemChanged.connect(self.on_subtitle_edited)
        
        # Connect both filter inputs to the same slot
        self.inspector.search_text.textChanged.connect(self.filter_tree)
        self.inspector.find_text.textChanged.connect(self.filter_tree)
        self.inspector.search_type_combo.currentIndexChanged.connect(self.filter_tree)

        # Connect returnPressed signals to replace_all_button
        self.inspector.find_text.returnPressed.connect(self.inspector.replace_all_button.click)
        self.inspector.replace_text.returnPressed.connect(self.inspector.replace_all_button.click)


    def populate_table(self, subs_data, hide=False):
        # The OriginalTextRole is a UI-specific concept for tracking edits.
        # We need to handle it here before passing data to the logic function.
        self.tree.blockSignals(True)
        # Clear previous data and reset OriginalTextRole
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item:
                item.setData(2, self.OriginalTextRole, None)
        self.tree.clear()

        ui_logic.populate_table(self.tree, self.ui_model, subs_data, hide)

        # After populating, we set the initial OriginalTextRole for all items.
        # This is crucial for the diff logic to work correctly later.
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item:
                original_text = item.text(2)
                item.setData(2, self.OriginalTextRole, original_text)
        self.tree.blockSignals(False)

    def filter_tree(self):
        """
        Updates the UI model with the current filter criteria from the UI,
        then calls the logic function to apply the filter.
        """
        self.ui_model.search_text = self.inspector.search_text.text()
        self.ui_model.find_text = self.inspector.find_text.text()
        self.ui_model.filter_type = self.inspector.search_type_combo.currentText()
        
        ui_logic.filter_tree(self.tree, self.ui_model)

    def find_next(self):
        """
        Updates the UI model with the current find text,
        then calls the logic function to find the next occurrence.
        """
        self.ui_model.find_text = self.inspector.find_text.text()
        ui_logic.find_next(self.tree, self.ui_model)



    def on_subtitle_edited(self, item, column):
        style_config = {
            'delete': '<font color="red"><s>{text}</s></font>',
            'replace': '<font color="blue">{text}</font>',
            'insert': '<font color="blue">{text}</font>',
        }

        clean_new_text, html_text, was_reverted = ui_logic.handle_subtitle_edited(
            item, column, self.OriginalTextRole, style_config
        )

        if clean_new_text is None:
            return

        self.tree.blockSignals(True)
        if was_reverted:
            item.setText(1, str(len(clean_new_text)))
            item.setData(2, self.OriginalTextRole, None)
            item.setText(2, html_text)
            item.setData(2, Qt.UserRole, clean_new_text)
        else:
            item.setText(1, str(len(clean_new_text)))
            item.setText(2, html_text)
            item.setData(2, Qt.UserRole, clean_new_text)
        self.tree.blockSignals(False)

        try:
            item_index = int(item.text(0))
            self.subtitleDataChanged.emit(item_index, clean_new_text)
        except (ValueError, TypeError):
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

        style_config = {
            'delete': '<font color="red"><s>{text}</s></font>',
            'replace': '<font color="blue">{text}</font>',
            'insert': '<font color="blue">{text}</font>',
        }
        
        self.tree.blockSignals(True)
        ui_logic.update_item_for_replace(
            item, original_text, new_text, self.OriginalTextRole, style_config
        )
        self.tree.blockSignals(False)

    def get_all_subtitles_data(self):
        return ui_logic.get_all_subtitles_data(self.tree)


    def update_all_items_for_replace(self, changes):
        """Updates all changed items with diff highlighting."""
        style_config = {
            'delete': '<font color="red"><s>{text}</s></font>',
            'replace': '<font color="blue">{text}</font>',
            'insert': '<font color="blue">{text}</font>',
        }
        ui_logic.update_all_items_for_replace(
            self.tree, changes, self.find_item_by_id, self.OriginalTextRole, style_config
        )
