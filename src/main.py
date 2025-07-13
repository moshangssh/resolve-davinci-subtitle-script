# main.py
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

import os

from src.resolve_integration import ResolveIntegration
from src.timecode_utils import TimecodeUtils
from src.ui import SubvigatorWindow
from src.subtitle_manager import SubtitleManager

class ApplicationController:
    def __init__(self, resolve_integration, subtitle_manager, timecode_utils):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.resolve_integration = resolve_integration
        self.subtitle_manager = subtitle_manager
        self.timecode_utils = timecode_utils
        self.window = SubvigatorWindow(self.resolve_integration)
        self.app.aboutToQuit.connect(self.cleanup_on_exit)
        
    def cleanup_on_exit(self):
        """
        Cleans up resources when the application is about to quit.
        """
        print("LOG: INFO: Application is about to quit. Cleaning up cache.")
        self.subtitle_manager.clear_cache()

    def connect_signals(self):
        self.window.refresh_button.clicked.connect(self.on_refresh_button_clicked)
        self.window.tree.itemClicked.connect(self.on_item_clicked)
        self.window.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.window.subtitleDataChanged.connect(self.on_subtitle_data_changed)
        self.window.search_text.returnPressed.connect(lambda: self.window.filter_tree(self.window.search_text.text()))
        self.window.track_combo.currentIndexChanged.connect(self.on_track_changed)
        self.window.export_reimport_button.clicked.connect(self.on_export_reimport_clicked)
        self.window.replace_button.clicked.connect(
            lambda: self.handle_replace_current()
        )
        self.window.replace_all_button.clicked.connect(
            lambda: self.handle_replace_all()
        )
 
 
    def show_error_message(self, text, title="操作失败"):
       """
       Displays a critical error message box.
       """
       msg_box = QMessageBox()
       msg_box.setIcon(QMessageBox.Critical)
       msg_box.setText(text)
       msg_box.setWindowTitle(title)
       msg_box.setStandardButtons(QMessageBox.Ok)
       msg_box.exec()

    def on_export_reimport_clicked(self):
        if self.window.track_combo.currentIndex() < 0:
           self.show_error_message("请先在DaVinci Resolve的时间线上选择一个轨道，然后再执行此操作。", "未选择轨道")
           return

        if self.subtitle_manager.current_json_path is None:
           print("LOG: ERROR: No JSON file path is set, please select a track first.")
           self.show_error_message("无法获取字幕文件。请重新获取。")
           return

        print("LOG: INFO: Starting export and re-import process.")
        success, error = self.resolve_integration.reimport_from_json_file(self.subtitle_manager.current_json_path)
        if error:
           self.show_error_message(f"导入/导出失败: {error}")
        else:
           self.subtitle_manager.is_dirty = False
           QMessageBox.information(self.window, "成功", "字幕已成功导入到新的轨道。")


    def on_track_changed(self, index):
        if index < 0:
            return

        track_index = index + 1
        success, error = self.resolve_integration.set_active_subtitle_track(track_index)
        if error:
           self.show_error_message(f"切换轨道失败: {error}")
           return

        subtitles = self.subtitle_manager.load_subtitles(track_index)
        self.window.populate_table(subs_data=subtitles)
        self.window.filter_tree(self.window.search_text.text())

    def on_refresh_button_clicked(self):
        if self.subtitle_manager.is_dirty:
            reply = QMessageBox.question(self.window, '未同步的修改',
                                         "您有未同步到DaVinci Resolve的修改。要继续刷新并放弃这些更改吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.resolve_integration.cache_all_subtitle_tracks()
        timeline_info, error = self.resolve_integration.get_current_timeline_info()
        if error:
           self.show_error_message(f"刷新失败: {error}")
           return
        if not timeline_info:
            self.show_error_message("未能获取时间线信息，请确保DaVinci Resolve中已打开项目和时间线。")
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
            sub_obj = next((s for s in self.subtitle_manager.get_subtitles() if s['index'] == item_id), None)

            if not sub_obj:
                print(f"LOG: WARNING: Failed to get subtitle object for ID {item_id}")
                return

            timeline_info, error = self.resolve_integration.get_current_timeline_info()
            if error:
               self.show_error_message(f"无法导航到时间码: {error}")
               return
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

    def on_subtitle_data_changed(self, item_index, new_text):
        """
        This slot is connected to the UI's subtitleDataChanged signal.
        It receives clean data directly from the UI after an edit is finalized.
        """
        try:
            # The subtitle_manager should be updated with the clean text
            if self.subtitle_manager.update_subtitle_text(item_index, new_text):
                print(f"LOG: INFO: Updated subtitle {item_index} in data and file with clean text.")
            else:
                print(f"LOG: ERROR: Failed to update subtitle {item_index} with clean text.")

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
            # Directly update the single subtitle in the data model,
            # which is more efficient than a full refresh.
            self.subtitle_manager.update_subtitle_text(change['index'], change['new'])
            self.window.find_next()
 
    def handle_replace_all(self):
        """Handles replacing text across all subtitle items."""
        find_text = self.window.find_text.text()
        replace_text = self.window.replace_text.text()
        
        changes = self.subtitle_manager.handle_replace_all(find_text, replace_text)
        
        if changes:
            self.window.update_all_items_for_replace(changes)
            # After updating the UI, directly save the changes in the manager
            self.subtitle_manager._save_changes_to_json()
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
        subtitle_manager = SubtitleManager(resolve_integration)
        timecode_utils = TimecodeUtils(resolve_integration.resolve)
        controller = ApplicationController(
            resolve_integration=resolve_integration,
            subtitle_manager=subtitle_manager,
            timecode_utils=timecode_utils
        )
        controller.run()
    except ImportError as e:
        print(f"LOG: CRITICAL: Error initializing application: {e}")
        # Optionally, show a GUI message box here
        sys.exit(1)

if __name__ == '__main__':
    main()