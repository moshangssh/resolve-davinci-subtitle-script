# Merged script for DaVinci Resolve
# Original files: main.py, resolve_integration.py, timecode_utils.py, ui.py

import sys
import os
import platform
import math
import cffi
from PySide6.QtWidgets import (
    QApplication,
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
)
from PySide6.QtCore import Qt

# --- timecode_utils.py ---
class TimecodeUtils:
    def __init__(self, resolve):
        self.resolve = resolve
        self.ffi = cffi.FFI()
        self._define_c_types()
        self.libavutil = self._load_library()

    def _define_c_types(self):
        self.ffi.cdef("""
            enum AVTimecodeFlag {
                AV_TIMECODE_FLAG_DROPFRAME      = 1<<0,
                AV_TIMECODE_FLAG_24HOURSMAX     = 1<<1,
                AV_TIMECODE_FLAG_ALLOWNEGATIVE  = 1<<2,
            };

            struct AVRational { int32_t num; int32_t den; };
            struct AVTimecode {
                int32_t start;
                enum AVTimecodeFlag flags;
                struct AVRational rate;
                uint32_t fps;
            };

            char* av_timecode_make_string(const struct AVTimecode* tc, const char* buf, int32_t framenum);
            int32_t av_timecode_init_from_string(struct AVTimecode* tc, struct AVRational rate, const char* str, void* log_ctx);
            const char* av_version_info(void);
        """)

    def _load_library(self):
        if not self.resolve:
            raise ImportError("Resolve object not provided to TimecodeUtils.")

        try:
            fu = self.resolve.Fusion()
        except AttributeError:
            raise ImportError("Could not get Fusion object from Resolve. Is Fusion running?")

        lib_name_pattern = ""
        if platform.system() == "Windows":
            lib_name_pattern = "avutil*.dll"
        elif platform.system() == "Darwin": # OSX
            lib_name_pattern = "libavutil*.dylib"
        else: # Linux
            lib_name_pattern = "libavutil.so"
            
        fusion_libs_path = fu.MapPath("FusionLibs:")
        
        # On non-Windows, the path might be one level up
        if platform.system() != "Windows":
             fusion_libs_path = os.path.abspath(os.path.join(fusion_libs_path, '..'))

        # Search for the library in the FusionLibs directory
        import glob
        lib_path_search = os.path.join(fusion_libs_path, lib_name_pattern)
        found_libs = glob.glob(lib_path_search)

        if not found_libs:
            raise ImportError(f"Could not find library matching '{lib_name_pattern}' in '{fusion_libs_path}'")
        
        # Take the first match
        lib_path = found_libs[0]

        try:
            print(f"Attempting to load library from DaVinci Resolve's path: {lib_path}")
            return self.ffi.dlopen(lib_path)
        except OSError as e:
            error_message = (
                f"Failed to load '{lib_path}' from Resolve's internal directory.\n"
                f"Error: {e}\n"
                "This might indicate a problem with the Resolve installation or permissions."
            )
            raise ImportError(error_message)

    def get_frame_rates(self):
        return [16, 18, 23.976, 24, 25, 29.97, 30, 47.952, 48, 50, 59.94, 60, 72, 95.904, 96, 100, 119.88, 120]

    def get_fraction(self, frame_rate_string_or_number):
        frame_rate = float(str(frame_rate_string_or_number))
        for fr in self.get_frame_rates():
            if fr == frame_rate or math.floor(fr) == frame_rate:
                is_decimal = fr % 1 > 0
                denominator = 1001 if is_decimal else 100
                numerator = math.ceil(fr) * (1000 if is_decimal else denominator)
                return {'num': int(numerator), 'den': int(denominator)}
        raise ValueError(f"Invalid frame rate: {frame_rate_string_or_number}")

    def get_decimal(self, frame_rate_string_or_number):
        fraction = self.get_fraction(frame_rate_string_or_number)
        return float(f"{fraction['num'] / fraction['den']:.3f}")

    def frame_from_timecode(self, timecode, frame_rate):
        rate_frac = self.get_fraction(frame_rate)
        tc = self.ffi.new("struct AVTimecode *")
        rate = self.ffi.new("struct AVRational", rate_frac)
        timecode_bytes = timecode.encode('utf-8')
        
        result = self.libavutil.av_timecode_init_from_string(tc, rate, timecode_bytes, self.ffi.NULL)
        if result != 0:
            raise RuntimeError(f"avutil error code: {result}")
        return tc.start

    def timecode_from_frame(self, frame, frame_rate, drop_frame=False):
        # 1. 获取帧率的十进制表示
        decimal_fps = self.get_decimal(frame_rate)

        # 2. 构造 AVTimecode 结构体所需的 flags
        flags_value = 0
        if drop_frame:
            flags_value |= 1  # AV_TIMECODE_FLAG_DROPFRAME
        flags_value |= 2      # AV_TIMECODE_FLAG_24HOURSMAX

        # 3. 使用 cffi 创建 AVTimecode 结构体实例
        tc = self.ffi.new("struct AVTimecode *", {
            'start': 0,
            'flags': flags_value,
            'rate': {'num': 0, 'den': 0}, # 显式初始化
            'fps': math.ceil(decimal_fps)
        })

        # 4. 准备调用 av_timecode_make_string 所需的缓冲区
        buf = self.ffi.new("char[30]")

        # 5. 调用 C 函数
        result_ptr = self.libavutil.av_timecode_make_string(tc, buf, frame)

        # 6. 检查返回指针是否为空
        if result_ptr == self.ffi.NULL:
            return "00:00:00:00" # 或抛出异常

        # 7. 将返回的C字符串转换为Python字符串
        timecode_string = self.ffi.string(result_ptr).decode('utf-8')

        return timecode_string

# --- resolve_integration.py ---
class ResolveIntegration:
    def __init__(self):
        self.resolve = self._get_resolve_instance()
        if not self.resolve:
            raise ImportError("Could not connect to DaVinci Resolve. Make sure the application is running.")
        
        self.project_manager = self.resolve.GetProjectManager()
        self.project = self.project_manager.GetCurrentProject()
        self.timeline = self.project.GetCurrentTimeline()

    def _get_resolve_instance(self):
        try:
            import fusionscript
            return fusionscript.scriptapp("Resolve")
        except ImportError:
            try:
                import DaVinciResolveScript as dvr_script
                return dvr_script.scriptapp("Resolve")
            except ImportError:
                return None

    def get_current_timeline_info(self):
        if not self.timeline:
            return None
        return {
            'frame_rate': self.timeline.GetSetting('timelineFrameRate'),
            'track_count': self.timeline.GetTrackCount('subtitle'),
        }

    def get_subtitles(self, track_number=1):
        if not self.timeline:
            return []
        return self.timeline.GetItemListInTrack('subtitle', track_number)

# --- ui.py ---
class NumericTreeWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        # Ensure the 'other' item is comparable
        if not isinstance(other, QTreeWidgetItem):
            return super().__lt__(other)

        try:
            # Compare based on the integer value of the first column
            return int(self.text(0)) < int(other.text(0))
        except (ValueError, TypeError, AttributeError):
            # Fallback to default string comparison if conversion fails
            return super().__lt__(other)

class SubvigatorWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Andy's Subvigator (Python Port)")
        self.setGeometry(100, 100, 380, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_widgets()
        self._setup_layouts()

    def _create_widgets(self):
        self.search_label = QLabel("Filter:")
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Search Text Filter")
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(['Contains', 'Exact', 'Starts With', 'Ends With', 'Wildcard'])

        self.dynamic_search_checkbox = QCheckBox("Dynamic search text")
        self.drop_frame_checkbox = QCheckBox("DF navigation")

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['#', 'Subtitle', 'StartFrame'])
        self.tree.setColumnWidth(0, 58)
        self.tree.setColumnWidth(1, 280)
        self.tree.setColumnHidden(2, True)

        self.track_combo = QComboBox()
        self.combine_subs_label = QLabel("Combine Subs:")
        self.combine_subs_combo = QComboBox()
        self.combine_subs_combo.addItems([str(i) for i in range(1, 11)])
        self.refresh_button = QPushButton("Refresh")

    def _setup_layouts(self):
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_text)
        search_layout.addWidget(self.search_type_combo)
        self.main_layout.addLayout(search_layout)

        options_layout = QHBoxLayout()
        options_layout.addWidget(self.dynamic_search_checkbox)
        options_layout.addWidget(self.drop_frame_checkbox)
        self.main_layout.addLayout(options_layout)

        self.main_layout.addWidget(self.tree)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.track_combo)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.combine_subs_label)
        bottom_layout.addWidget(self.combine_subs_combo)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.refresh_button)
        self.main_layout.addLayout(bottom_layout)

    def populate_table(self, subs_data, hide=False):
        self.tree.clear()
        for i, sub_obj in subs_data.items():
            item = NumericTreeWidgetItem(self.tree)
            item.setText(0, str(i))
            item.setText(1, sub_obj.GetName())
            item.setText(2, str(sub_obj.GetStart()))
            if hide:
                item.setHidden(True)
        self.tree.sortItems(0, Qt.AscendingOrder)

# --- main.py ---
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

    def refresh_data(self):
        timeline_info = self.resolve_integration.get_current_timeline_info()
        if not timeline_info:
            return

        self.window.track_combo.clear()
        for i in range(1, timeline_info['track_count'] + 1):
            self.window.track_combo.addItem(f"ST {i}")

        track_index = self.window.track_combo.currentIndex() + 1
        subtitles = self.resolve_integration.get_subtitles(track_index)
        
        subs_data = {i + 1: sub for i, sub in enumerate(subtitles)}
        self.window.populate_table(subs_data)

    def on_item_clicked(self, item, column):
        start_frame_str = item.text(2)
        if start_frame_str:
            start_frame = int(start_frame_str)
            timeline_info = self.resolve_integration.get_current_timeline_info()
            frame_rate = timeline_info['frame_rate']
            drop_frame = self.window.drop_frame_checkbox.isChecked()
            
            timecode = self.timecode_utils.timecode_from_frame(start_frame, frame_rate, drop_frame)
            
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
            item.setHidden(search_text.lower() not in item.text(1).lower())

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