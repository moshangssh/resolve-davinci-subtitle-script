import re
import difflib
from PySide6.QtCore import Qt
from .ui_model import UIModel

def _generate_diff_html(original_text, new_text, style_config):
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

def get_all_subtitles_data(tree):
    """
    Retrieves all subtitle entries from the tree as a list of dictionaries,
    ensuring the text is the clean, underlying data, not the display HTML.
    """
    subs_data = []
    root = tree.invisibleRootItem()
    for i in range(root.childCount()):
        item = root.child(i)
        
        # Prioritize UserRole for the most up-to-date clean text
        clean_text = item.data(2, Qt.UserRole)
        
        # If UserRole is not set (e.g., for unmodified items), get the display text and clean it
        if clean_text is None:
            clean_text = re.sub(r'<[^>]+>', '', item.text(2))

        try:
            index = int(item.text(0))
        except (ValueError, TypeError):
            index = -1 # Or some other default

        try:
            start_frame = int(item.text(5))
        except (ValueError, TypeError):
            start_frame = -1 # Or some other default

        subs_data.append({
            'id': index,
            'index': index,
            'text': clean_text,
            'start': item.text(3),
            'end': item.text(4),
            'in_frame': start_frame,
        })
    return subs_data

def _match_text(text, filter_text, filter_type):
    """Helper function to perform the actual text matching logic."""
    if not filter_text:
        return True
    if filter_type == '包含':
        return filter_text in text
    elif filter_type == '精确':
        return filter_text == text
    elif filter_type == '开头是':
        return text.startswith(filter_text)
    elif filter_type == '结尾是':
        return text.endswith(filter_text)
    elif filter_type == '通配符':
        try:
            regex_pattern = '^' + '.*'.join(re.escape(part) for part in filter_text.split('*')) + '$'
            return re.search(regex_pattern, text) is not None
        except re.error:
            return False # Invalid regex
    return False

def populate_table(tree, ui_model: UIModel, subs_data, hide=False):
    """Populates the tree widget with subtitle data and updates the UI model."""
    from .ui_components import NumericTreeWidgetItem
    from PySide6.QtCore import Qt

    tree.blockSignals(True)
    tree.clear()

    if not subs_data:
        ui_model.displayed_subtitles = []
        tree.blockSignals(False)
        return

    displayed_subs = []
    for sub in subs_data:
        item = NumericTreeWidgetItem(tree)
        item.setText(0, str(sub.get('index', sub.get('id', ''))))
        text = sub.get('text', '')
        item.setText(1, str(len(text)))
        item.setText(2, text)
        item.setData(2, Qt.UserRole, text)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setText(3, sub.get('start', sub.get('in_timecode', '')))
        item.setText(4, sub.get('end', sub.get('out_timecode', '')))
        item.setText(5, str(sub.get('in_frame', '')))
        if hide:
            item.setHidden(True)
        displayed_subs.append(sub)

    tree.sortItems(0, Qt.AscendingOrder)
    tree.blockSignals(False)
    ui_model.displayed_subtitles = displayed_subs


def filter_tree(tree, ui_model: UIModel):
    """Filters the tree based on search and find criteria from the UI model."""
    root = tree.invisibleRootItem()

    for i in range(root.childCount()):
        item = root.child(i)
        subtitle_text = item.text(2)

        # Check primary filter
        search_matches = _match_text(subtitle_text, ui_model.search_text, ui_model.filter_type)
        
        # Check find filter (always 'Contains')
        find_matches = not ui_model.find_text or ui_model.find_text in subtitle_text

        # Both must match
        item.setHidden(not (search_matches and find_matches))

def find_next(tree, ui_model: UIModel):
    """Finds the next occurrence of text in the tree."""
    from PySide6.QtWidgets import QTreeWidgetItemIterator

    if not ui_model.find_text:
        return

    start_item = tree.currentItem()
    item_iterator = QTreeWidgetItemIterator(tree, QTreeWidgetItemIterator.All)
    
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
        if ui_model.find_text in item.text(2):
            tree.setCurrentItem(item)
            tree.scrollToItem(item)
            return
        item_iterator += 1
    
    # If we reached the end, wrap around and search from the beginning
    item_iterator = QTreeWidgetItemIterator(tree, QTreeWidgetItemIterator.All)
    while item_iterator.value() and item_iterator.value() != start_item:
        item = item_iterator.value()
        if ui_model.find_text in item.text(2):
            tree.setCurrentItem(item)
            tree.scrollToItem(item)
            return
        item_iterator += 1

    # Check the start item itself if we've wrapped
    if start_item and ui_model.find_text in start_item.text(2) and tree.currentItem() != start_item:
         tree.setCurrentItem(start_item)
         tree.scrollToItem(start_item)

def handle_subtitle_edited(item, column, original_text_role, style_config):
    """
    Handles the logic for when a subtitle item is edited.
    Returns a tuple: (clean_new_text, html_text, was_reverted)
    """
    import re
    from PySide6.QtCore import Qt

    if column != 2:
        return None, None, False

    new_text = item.text(2)
    clean_new_text = re.sub(r'<[^>]+>', '', new_text)
    
    original_text = item.data(2, original_text_role)
    
    if original_text is None:
        original_text = item.data(2, Qt.UserRole)

    if original_text is None:
        original_text = ""
    
    if clean_new_text == original_text:
        # Text was reverted to original
        return original_text, original_text, True

    html_text = _generate_diff_html(original_text, clean_new_text, style_config)
    
    return clean_new_text, html_text, False

def update_item_for_replace(item, original_text, new_text, original_text_role, style_config):
    """Updates a single item's text with diff highlighting for replacement."""
    from PySide6.QtCore import Qt

    if not item:
        return

    # If this is the first replacement, store the original text
    if item.data(2, original_text_role) is None:
        item.setData(2, original_text_role, original_text)

    # The original_text for the diff should be the one from OriginalTextRole if available
    base_text = item.data(2, original_text_role) or original_text

    diff_html = _generate_diff_html(base_text, new_text, style_config)

    item.setText(2, diff_html)
    item.setData(2, Qt.UserRole, new_text) # Update the user role with the new clean text

def update_all_items_for_replace(tree, changes, find_item_by_id_func, original_text_role, style_config):
    """Updates all changed items with diff highlighting."""
    from PySide6.QtCore import Qt

    tree.blockSignals(True)
    for change in changes:
        item = find_item_by_id_func(change['index'])
        if item:
            # If this is the first replacement for this item, store its original text
            if item.data(2, original_text_role) is None:
                item.setData(2, original_text_role, change['old'])
            
            # The original_text for the diff should be the one from OriginalTextRole if available
            base_text = item.data(2, original_text_role) or change['old']

            diff_html = _generate_diff_html(base_text, change['new'], style_config)
            item.setText(2, diff_html)
            item.setData(2, Qt.UserRole, change['new'])

    tree.blockSignals(False)