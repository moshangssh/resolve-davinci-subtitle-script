# ui_components.py
from PySide6.QtWidgets import (
    QStyledItemDelegate,
    QStyle,
    QTreeWidgetItem,
    QLineEdit,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument, QPalette, QColor, QPainter, QPen, QBrush
import re

class CharCountDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        # This column is not editable, so we return None.
        return None

    def paint(self, painter: QPainter, option, index):
        # We don't call super().paint() because in a test environment, it can cause issues
        # and we only want to test our custom drawing logic anyway.
        # super().paint(painter, option, index)

        # Manually draw the background for selection state
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        char_count_str = index.data()
        if not char_count_str or not char_count_str.isdigit():
            return

        char_count = int(char_count_str)

        # Determine color based on character count
        color = QColor("#28a745") if char_count <= 15 else QColor("#dc3545")

        # --- Circle Drawing Logic ---
        rect = option.rect
        # Make the circle a bit smaller than the cell height
        diameter = min(rect.width(), rect.height()) - 14
        radius = diameter / 2.0

        # Center the circle in the cell
        x = rect.x() + (rect.width() - diameter) / 2
        y = rect.y() + (rect.height() - diameter) / 2

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the circle background
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen) # No border for the circle
        painter.drawEllipse(x, y, diameter, diameter)

        # --- Text Drawing Logic ---
        # Set text color
        painter.setPen(QPen(Qt.white))
        # Set font size relative to circle size
        font = painter.font()
        font.setPixelSize(int(radius))
        painter.setFont(font)
        
        # Draw text centered in the circle
        painter.drawText(int(x), int(y), int(diameter), int(diameter), Qt.AlignCenter, char_count_str)

        painter.restore()

class HtmlDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(HtmlDelegate, self).__init__(parent)
        self.doc = QTextDocument(self)

    def createEditor(self, parent, option, index):
        # Only create an editor for columns that should be editable.
        if index.column() in [2, 3, 4]: # Subtitle, In, Out
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