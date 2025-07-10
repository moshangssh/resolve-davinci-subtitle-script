# main.py
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

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
        self.window.refresh_button.clicked.connect(self.on_refresh_button_clicked)
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
        if self.window.track_combo.currentIndex() < 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("请先在DaVinci Resolve的时间线上选择一个轨道，然后再执行此操作。")
            msg_box.setWindowTitle("未选择轨道")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
            return

        if self.subtitle_manager.current_json_path is None:
            print("LOG: ERROR: No JSON file path is set, please select a track first.")
            # Also show a message box here for consistency, as this is a fallback.
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("无法获取轨道文件路径。请刷新并重试。")
            msg_box.setWindowTitle("操作失败")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
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

    def on_refresh_button_clicked(self):
        self.resolve_integration.cache_all_subtitle_tracks()
        timeline_info = self.resolve_integration.get_current_timeline_info()
        if not timeline_info:
            return

        self.window.track_combo.clear()
        for i in range(1, timeline_info['track_count'] + 1):
            self.window.track_combo.addItem(f"ST {i}")

        # Manually trigger the on_track_changed for the initial load
        if self.window.track_combo.count() > 0:
            self.on_track_changed(self.window.track_combo.currentIndex())

    def refresh_data(self):
        pass

    def on_item_clicked(self, item, column):
        try:
            item_id_str = item.text(0)
            if not item_id_str:
                return

            item_id = int(item_id_str)
            sub_obj = next((s for s in self.subtitle_manager.get_subtitles() if s['index'] == item_id), None)

            if not sub_obj:
                print(f"LOG: WARNING: Failed to get subtitle object for ID {item_id}")
                return

            timeline_info = self.resolve_integration.get_current_timeline_info()
            if not timeline_info:
                print("LOG: WARNING: Could not get timeline info.")
                return

            frame_rate = timeline_info['frame_rate']
            start_timecode_str = sub_obj['start']

            # Convert HH:MM:SS,ms to total frames
            total_frames = self.timecode_utils.timecode_to_frames(start_timecode_str, frame_rate)
            
            # Convert total frames to HH:MM:SS:FF for Resolve
            resolve_timecode = self.timecode_utils.timecode_from_frame(total_frames, frame_rate)
            
            self.resolve_integration.timeline.SetCurrentTimecode(resolve_timecode)
            print(f"LOG: INFO: Navigated to timecode: {resolve_timecode} (Frame: {total_frames})")

        except (ValueError, IndexError) as e:
            print(f"LOG: WARNING: Failed to process item click for ID {item_id_str}: {e}")


    def on_item_double_clicked(self, item, column):
        if column == 1: # Only allow editing the 'Subtitle' column
            self.window.tree.editItem(item, column)

    def on_item_changed(self, item, column):
        if column == 1:
            try:
                item_index = int(item.text(0))
                new_text = item.text(1)
                
                if self.subtitle_manager.update_subtitle_text(item_index, new_text):
                    print(f"LOG: INFO: Updated subtitle {item_index} in data and file.")
                else:
                    print(f"LOG: ERROR: Failed to update subtitle {item_index}.")
 
            except (ValueError, KeyError) as e:
                print(f"LOG: ERROR: Failed to update subtitle due to invalid data: {e}")
            except Exception as e:
                print(f"LOG: ERROR: An unexpected error occurred while updating subtitle: {e}")
 
    def handle_replace_current(self):
        """Handles replacing the text of a single subtitle item."""
        current_item = self.window.tree.currentItem()
        if not current_item:
            return
            
        item_index = int(current_item.text(0))
        find_text = self.window.find_text.text()
        replace_text = self.window.replace_text.text()

        change = self.subtitle_manager.handle_replace_current(item_index, find_text, replace_text)
        
        if change:
            self.window.update_item_for_replace(change['index'], change['old'], change['new'])
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