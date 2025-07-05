import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui import SubvigatorWindow
from resolve_integration import ResolveIntegration
from timecode_utils import TimecodeUtils

class ApplicationController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        try:
            self.resolve_integration = ResolveIntegration()
            self.timecode_utils = TimecodeUtils()
        except ImportError as e:
            # In a real application, you'd show a proper error dialog.
            print(f"Error: {e}")
            sys.exit(1)

        self.window = SubvigatorWindow()
        
        self.connect_signals()
        self.refresh_data()

    def connect_signals(self):
        self.window.refresh_button.clicked.connect(self.refresh_data)
        self.window.tree.itemClicked.connect(self.on_item_clicked)
        self.window.search_text.returnPressed.connect(self.filter_subtitles)
        # Add other signal connections here based on the Lua script's logic

    def refresh_data(self):
        timeline_info = self.resolve_integration.get_current_timeline_info()
        if not timeline_info:
            # Handle case with no timeline
            return

        # Populate track combo
        self.window.track_combo.clear()
        for i in range(1, timeline_info['track_count'] + 1):
            self.window.track_combo.addItem(f"ST {i}")

        # Get subtitles and populate table
        track_index = self.window.track_combo.currentIndex() + 1
        subtitles = self.resolve_integration.get_subtitles(track_index)
        
        subs_data = {i + 1: sub.GetName() for i, sub in enumerate(subtitles)}
        self.window.populate_table(subs_data)

    def on_item_clicked(self, item, column):
        # Placeholder for navigating the timeline
        start_frame_str = item.text(2) # Assuming start frame is stored in a hidden column 2
        if start_frame_str:
            start_frame = int(start_frame_str)
            timeline_info = self.resolve_integration.get_current_timeline_info()
            frame_rate = timeline_info['frame_rate']
            drop_frame = self.window.drop_frame_checkbox.isChecked()
            
            timecode = self.timecode_utils.timecode_from_frame(start_frame, frame_rate, drop_frame)
            
            # This is where you would call the Resolve API to set the timecode
            # self.resolve_integration.timeline.SetCurrentTimecode(timecode)
            print(f"Would navigate to timecode: {timecode}")


    def filter_subtitles(self):
        search_text = self.window.search_text.text()
        if not search_text:
            for i in range(self.window.tree.topLevelItemCount()):
                self.window.tree.topLevelItem(i).setHidden(False)
            return

        # This is a basic search. The Lua script has more complex matching logic.
        for i in range(self.window.tree.topLevelItemCount()):
            item = self.window.tree.topLevelItem(i)
            item.setHidden(search_text.lower() not in item.text(1).lower())

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())

if __name__ == '__main__':
    controller = ApplicationController()
    controller.run()