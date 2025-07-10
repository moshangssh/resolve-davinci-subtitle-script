# main.py
import sys
from PySide6.QtWidgets import QApplication

import os

from resolve_integration import ResolveIntegration
from timecode_utils import TimecodeUtils
from ui import SubvigatorWindow
from subtitle_manager import SubtitleManager
from data_model import DataModel

class ApplicationController:
    def __init__(self, resolve_integration, subtitle_manager, data_model, timecode_utils):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.resolve_integration = resolve_integration
        self.subtitle_manager = subtitle_manager
        self.data_model = data_model
        self.timecode_utils = timecode_utils
        self.window = SubvigatorWindow(self.resolve_integration)
        
    def connect_signals(self):
        self.window.refresh_button.clicked.connect(self.refresh_data)
        self.window.tree.itemClicked.connect(self.on_item_clicked)
        self.window.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.window.tree.itemChanged.connect(self.on_item_changed)
        self.window.search_text.returnPressed.connect(lambda: self.window.filter_tree(self.window.search_text.text()))
        self.window.track_combo.currentIndexChanged.connect(self.on_track_changed)
        self.window.export_reimport_button.clicked.connect(self.on_export_reimport_clicked)
        self.window.replace_button.clicked.connect(
            lambda: self.handle_replace_current()
        )
        self.window.replace_all_button.clicked.connect(
            lambda: self.handle_replace_all()
        )
 
 
    def on_export_reimport_clicked(self):
        if self.subtitle_manager.current_json_path is None:
            print("LOG: ERROR: No JSON file path is set, please select a track first.")
            return
        print("LOG: INFO: Starting export and re-import process.")
        self.resolve_integration.reimport_from_json_file(self.subtitle_manager.current_json_path)
        self.refresh_data()
 
    def on_track_changed(self, index):
        if index < 0:
            return

        track_index = index + 1
        self.resolve_integration.set_active_subtitle_track(track_index)
        subtitles = self.subtitle_manager.load_subtitles(track_index)
        self.window.populate_table(subs_data=subtitles)
        self.window.filter_tree(self.window.search_text.text())

    def refresh_data(self):
        timeline_info = self.resolve_integration.get_current_timeline_info()
        if not timeline_info:
            return

        self.window.track_combo.clear()
        for i in range(1, timeline_info['track_count'] + 1):
            self.window.track_combo.addItem(f"ST {i}")

        # Manually trigger the on_track_changed for the initial load
        if self.window.track_combo.count() > 0:
            self.on_track_changed(self.window.track_combo.currentIndex())

    def on_item_clicked(self, item, column):
        try:
            item_id_str = item.text(0)
            if not item_id_str:
                return

            item_id = int(item_id_str)

            # Find the corresponding subtitle object from the stored data
            sub_obj = next((s for s in self.subtitle_manager.get_subtitles() if s['id'] == item_id), None)
 
            if sub_obj:
                start_frame = sub_obj['in_frame']
                timeline_info = self.resolve_integration.get_current_timeline_info()
                frame_rate = timeline_info['frame_rate']
                drop_frame = self.resolve_integration.timeline.GetSetting('timelineDropFrame') == '1'

                timecode = self.timecode_utils.timecode_from_frame(start_frame, frame_rate, drop_frame)

                self.resolve_integration.timeline.SetCurrentTimecode(timecode)
                print(f"LOG: INFO: Navigated to timecode: {timecode}")
            else:
                print(f"LOG: WARNING: Failed to get subtitle object for ID {item_id}")
        except (ValueError, IndexError):
            print(f"LOG: WARNING: Failed to get subtitle object for ID {item_id_str}")


    def on_item_double_clicked(self, item, column):
        if column == 1: # Only allow editing the 'Subtitle' column
            self.window.tree.editItem(item, column)

    def on_item_changed(self, item, column):
        if column == 1:
            try:
                item_id = int(item.text(0))
                new_text = item.text(1)
                
                if self.subtitle_manager.update_subtitle_text(item_id, new_text):
                    print(f"LOG: INFO: Updated subtitle {item_id} in data and file.")
                else:
                    print(f"LOG: ERROR: Failed to update subtitle {item_id}.")
 
            except (ValueError, KeyError) as e:
                print(f"LOG: ERROR: Failed to update subtitle due to invalid data: {e}")
            except Exception as e:
                print(f"LOG: ERROR: An unexpected error occurred while updating subtitle: {e}")
 
    def handle_replace_current(self):
        """Handles replacing the text of a single subtitle item."""
        current_item = self.window.tree.currentItem()
        if not current_item:
            return
            
        item_id = int(current_item.text(0))
        find_text = self.window.find_text.text()
        replace_text = self.window.replace_text.text()

        change = self.subtitle_manager.handle_replace_current(item_id, find_text, replace_text)
        
        if change:
            self.window.update_item_for_replace(change['id'], change['old'], change['new'])
            self.window.find_next()
 
    def handle_replace_all(self):
        """Handles replacing text across all subtitle items."""
        find_text = self.window.find_text.text()
        replace_text = self.window.replace_text.text()
        
        changes = self.subtitle_manager.handle_replace_all(find_text, replace_text)
        
        if changes:
            self.window.update_all_items_for_replace(changes)
            self.window.find_text.clear()
            self.window.replace_text.clear()

    def run(self):
        self.connect_signals()
        self.refresh_data()
        self.window.show()
        sys.exit(self.app.exec())

def main():
    """Main function to run the application."""
    try:
        resolve_integration = ResolveIntegration()
        data_model = DataModel()
        subtitle_manager = SubtitleManager(resolve_integration, data_model)
        timecode_utils = TimecodeUtils(resolve_integration.resolve)
        controller = ApplicationController(
            resolve_integration=resolve_integration,
            subtitle_manager=subtitle_manager,
            data_model=data_model,
            timecode_utils=timecode_utils
        )
        controller.run()
    except ImportError as e:
        print(f"LOG: CRITICAL: Error initializing application: {e}")
        # Optionally, show a GUI message box here
        sys.exit(1)

if __name__ == '__main__':
    main()