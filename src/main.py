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
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        try:
            self.resolve_integration = ResolveIntegration()
            self.timecode_utils = TimecodeUtils(self.resolve_integration.resolve)
        except ImportError as e:
            print(f"Error: {e}")
            sys.exit(1)

        self.window = SubvigatorWindow()
        
    def connect_signals(self):
        self.window.refresh_button.clicked.connect(self.refresh_data)
        self.window.tree.itemClicked.connect(self.on_item_clicked)
        self.window.search_text.returnPressed.connect(self.filter_subtitles)
        self.window.track_combo.currentIndexChanged.connect(self.on_track_changed)
        self.window.track_combo.currentIndexChanged.connect(self.on_subtitle_track_selected)
 
    def on_subtitle_track_selected(self, index):
        if index > -1:
            track_index = index + 1
            self.resolve_integration.set_active_subtitle_track(track_index)
 
    def on_track_changed(self, index):
        track_index = index + 1
        if track_index == 0:
            return
 
        subs_data = self.resolve_integration.get_subtitles_with_timecode(track_index)
        self.window.populate_table(subs_data)
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
        start_frame_str = item.text(4)
        if start_frame_str:
            start_frame = int(start_frame_str)
            timeline_info = self.resolve_integration.get_current_timeline_info()
            frame_rate = timeline_info['frame_rate']
            timecode = self.timecode_utils.timecode_from_frame(start_frame, frame_rate)
            
            self.resolve_integration.timeline.SetCurrentTimecode(timecode)
            print(f"Navigated to timecode: {timecode}")

    def filter_subtitles(self):
        search_text = self.window.search_text.text()
        if not search_text:
            for i in range(self.window.tree.topLevelItemCount()):
                self.window.tree.topLevelItem(i).setHidden(False)
            return

        for i in range(self.window.tree.topLevelItemCount()):
            item = self.window.tree.topLevelItem(i)
            item.setHidden(search_text.lower() not in item.text(3).lower())

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