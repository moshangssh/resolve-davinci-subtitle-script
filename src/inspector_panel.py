# src/inspector_panel.py
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QFrame,
)

class InspectorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inspectorPanel") # For styling
        
        self._create_widgets()
        self._setup_layouts()

    def _create_widgets(self):
        # Filter Controls
        self.search_label = QLabel("筛选:")
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("搜索文本...")
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(['包含', '精确', '开头是', '结尾是', '通配符'])

        # Find and Replace widgets
        self.find_label = QLabel("查找:")
        self.find_text = QLineEdit()
        self.find_text.setPlaceholderText("查找内容...")
        self.replace_label = QLabel("替换:")
        self.replace_text = QLineEdit()
        self.replace_text.setPlaceholderText("替换为...")
        self.find_next_button = QPushButton("查找下一个")
        self.replace_button = QPushButton("替换")
        self.replace_all_button = QPushButton("全部替换")

        # Bottom controls
        self.track_combo = QComboBox()
        self.refresh_button = QPushButton("获取字幕")
        self.export_reimport_button = QPushButton("导出到DaVinci Resolve中")

    def _setup_layouts(self):
        inspector_layout = QVBoxLayout(self)
        inspector_layout.setContentsMargins(10, 10, 10, 10)
        inspector_layout.setSpacing(8)

        # --- Filter Controls ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_text)
        inspector_layout.addLayout(search_layout)
        inspector_layout.addWidget(self.search_type_combo)

        # --- Separator ---
        inspector_layout.addSpacing(10)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        inspector_layout.addWidget(separator)
        inspector_layout.addSpacing(10)

        # --- Find/Replace Controls ---
        inspector_layout.addWidget(self.find_label)
        inspector_layout.addWidget(self.find_text)
        inspector_layout.addWidget(self.replace_label)
        inspector_layout.addWidget(self.replace_text)

        find_replace_buttons_layout = QHBoxLayout()
        find_replace_buttons_layout.addWidget(self.find_next_button)
        find_replace_buttons_layout.addWidget(self.replace_button)
        find_replace_buttons_layout.addWidget(self.replace_all_button)
        inspector_layout.addLayout(find_replace_buttons_layout)

        inspector_layout.addStretch()

        # Bottom controls
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.track_combo)
        bottom_layout.addWidget(self.refresh_button)
        inspector_layout.addLayout(bottom_layout)
        inspector_layout.addWidget(self.export_reimport_button)