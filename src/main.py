# main.py
import sys
from PySide6.QtWidgets import QApplication

import os
# Add the parent directory of 'src' to the Python path
# This allows for absolute imports of modules within 'src'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.resolve_integration import ResolveIntegration
from src.timecode_utils import TimecodeUtils
from src.ui import SubvigatorWindow

class ApplicationController:
    def __init__(self, resolve_integration=None, timecode_utils=None):
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        try:
            self.resolve_integration = resolve_integration or ResolveIntegration()
            self.timecode_utils = timecode_utils or TimecodeUtils(self.resolve_integration.resolve)
        except ImportError as e:
            print(f"Error: {e}")
            raise SystemExit(1)

        self.window = SubvigatorWindow(self.resolve_integration)
        self.window.subtitles_data = []
        self.current_json_path = None
        self.raw_obj_map = {}
        
    def connect_signals(self):
        self.window.refresh_button.clicked.connect(self.refresh_data)
        self.window.tree.itemClicked.connect(self.on_item_clicked)
        self.window.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.window.tree.itemChanged.connect(self.on_item_changed)
        self.window.search_text.returnPressed.connect(self.filter_subtitles)
        self.window.track_combo.currentIndexChanged.connect(self.on_track_changed)
        self.window.track_combo.currentIndexChanged.connect(self.on_subtitle_track_selected)
        self.window.export_reimport_button.clicked.connect(self.on_export_reimport_clicked)
 
    def on_subtitle_track_selected(self, index):
        if index > -1:
            track_index = index + 1
            self.resolve_integration.set_active_subtitle_track(track_index)
 
    def on_export_reimport_clicked(self):
        current_track = self.window.track_combo.currentIndex()
        if current_track >= 0:
            self.resolve_integration.export_and_reimport_subtitles(current_track + 1)
            self.refresh_data()

    def on_track_changed(self, index):
        track_index = index + 1
        if track_index == 0:
            return

        # Export subtitles to JSON and get the path
        json_path = self.resolve_integration.export_subtitles_to_json(track_index)
        self.current_json_path = json_path
        
        # We still need the original data for the timecode jump functionality
        subs_data_with_raw = self.resolve_integration.get_subtitles_with_timecode(track_index)
        
        # Separate serializable data from non-serializable raw objects
        self.window.subtitles_data = []
        self.raw_obj_map = {}
        if subs_data_with_raw:
            for sub in subs_data_with_raw:
                self.raw_obj_map[sub['id']] = sub.pop('raw_obj', None)
                self.window.subtitles_data.append(sub)

        # Populate the table directly from the now-clean in-memory data
        self.window.populate_table(subs_data=self.window.subtitles_data)
        self.filter_subtitles()

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
            sub_obj = next((s for s in self.window.subtitles_data if s['id'] == item_id), None)

            if sub_obj:
                start_frame = sub_obj['in_frame']
                timeline_info = self.resolve_integration.get_current_timeline_info()
                frame_rate = timeline_info['frame_rate']
                drop_frame = self.resolve_integration.timeline.GetSetting('timelineDropFrame') == '1'

                timecode = self.timecode_utils.timecode_from_frame(start_frame, frame_rate, drop_frame)

                self.resolve_integration.timeline.SetCurrentTimecode(timecode)
                print(f"Navigated to timecode: {timecode}")
            else:
                print(f"Failed to get subtitle object for ID {item_id}")
        except (ValueError, IndexError):
            print(f"Failed to get subtitle object for ID {item_id_str}")

    def filter_subtitles(self):
        search_text = self.window.search_text.text()
        if not search_text:
            for i in range(self.window.tree.topLevelItemCount()):
                self.window.tree.topLevelItem(i).setHidden(False)
            return

        for i in range(self.window.tree.topLevelItemCount()):
            item = self.window.tree.topLevelItem(i)
            item.setHidden(search_text.lower() not in item.text(3).lower())

    def on_item_double_clicked(self, item, column):
        if column == 1: # Only allow editing the 'Subtitle' column
            self.window.tree.editItem(item, column)

    def on_item_changed(self, item, column):
        if column == 1:
            try:
                item_id = int(item.text(0))
                new_text = item.text(1)
                
                sub_obj = next((s for s in self.window.subtitles_data if s['id'] == item_id), None)
                
                if sub_obj:
                    sub_obj['text'] = new_text
                    self._save_changes_to_json()
                    # if not self.resolve_integration.update_subtitle_text(sub_obj, new_text):
                    #     print("Failed to update subtitle in Resolve.")

            except Exception as e:
                print(f"Failed to update subtitle: {e}")

    def _save_changes_to_json(self):
        if not self.current_json_path:
            print("Error: No current JSON file path is set. Cannot save.")
            return

        try:
            # Format the data to match the expected JSON structure before saving
            output_data = []
            for sub in self.window.subtitles_data:
                output_data.append({
                    "index": sub.get('id'),
                    "start": sub.get('in_timecode'),
                    "end": sub.get('out_timecode'),
                    "text": sub.get('text')
                })

            with open(self.current_json_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(output_data, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            print(f"Failed to auto-save subtitle changes: {e}")

    def run(self):
        self.connect_signals()
        self.refresh_data()
        self.window.show()
        sys.exit(self.app.exec())

def main():
    """Main function to run the application."""
    controller = ApplicationController()
    controller.run()

if __name__ == '__main__':
    main()