# 核心控制器: ApplicationController 分析

## 1. 概述

`ApplicationController` 是 `Subvigator` 应用的**核心控制器**，在应用的架构中扮演着至关重要的角色。它遵循了经典的**模型-视图-控制器 (MVC)** 设计思想，作为视图 (View) 和模型 (Model)/服务 (Service) 之间的协调者。

- **视图 (View)**: 由 [`SubvigatorWindow`](src/ui.py) 类及其子组件构成，负责展示用户界面和捕捉用户输入。
- **模型/服务 (Model/Service)**: 主要由 [`AppService`](src/services.py)、[`SubtitleManager`](src/subtitle_manager.py) 和 [`ResolveIntegration`](src/resolve_integration.py) 组成，负责处理业务逻辑、数据管理以及与 DaVinci Resolve 的交互。
- **控制器 (Controller)**: 即 `ApplicationController`，它的主要职责是：
    - 接收来自视图的用户操作信号（如按钮点击、下拉框选择等）。
    - 调用相应的服务层方法来执行业务逻辑。
    - 将服务层返回的数据传递给视图进行更新。
    - 管理核心组件的生命周期。

这种分层设计使得应用的各个部分职责分明，降低了耦合度，提高了代码的可维护性和可测试性。

## 2. 关键职责分析

### 2.1 组件初始化 (`__init__`)

在 `ApplicationController` 的构造函数中，它完成了所有核心组件的实例化和依赖注入。

```python
# src/main.py:14
class ApplicationController:
    def __init__(self, resolve_integration, subtitle_manager):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.resolve_integration = resolve_integration
        self.subtitle_manager = subtitle_manager
        # self.timecode_utils is now loaded on demand
        self.app_service = AppService(self.resolve_integration, self.subtitle_manager)
        self.window = SubvigatorWindow(self.resolve_integration)
        self.app.aboutToQuit.connect(self.cleanup_on_exit)
```

**初始化流程:**

1.  **`QApplication`**: 获取或创建一个 `QApplication` 实例，这是任何 PySide6 应用的基础。
2.  **`resolve_integration` & `subtitle_manager`**: 接收从 `main` 函数传入的 `ResolveIntegration` 和 `SubtitleManager` 实例。这是一种依赖注入的形式，使得控制器不负责创建这些核心依赖，方便测试和替换。
3.  **`AppService`**: 实例化 `AppService`，并将 `resolve_integration` 和 `subtitle_manager` 作为参数传入。`AppService` 封装了应用的主要业务逻辑。
4.  **`SubvigatorWindow`**: 实例化主窗口 `SubvigatorWindow`，它是应用UI的根节点。
5.  **`cleanup_on_exit`**: 连接 `QApplication` 的 `aboutToQuit` 信号到 `cleanup_on_exit` 槽函数，确保在应用退出时能够执行资源清理操作。

### 2.2 信号与槽的连接 (`connect_signals`)

此方法是控制器实现其协调者角色的关键。它将视图层（UI控件）发出的信号连接到控制器自身定义的槽函数上，从而响应用户的交互。

```python
# src/main.py:30
def connect_signals(self):
    # ... (connections)
```

**关键连接详情:**

| UI 控件 (在 `window.inspector` 或 `window.tree` 中) | 信号 | 控制器槽函数 | 实现的用户功能 |
| :--- | :--- | :--- | :--- |
| `refresh_button` | `clicked` | `on_refresh_button_clicked` | 刷新时间线信息，获取最新的轨道数量，并更新字幕轨道下拉框。 |
| `tree` | `itemClicked` | `on_item_clicked` | 当用户单击某条字幕时，在 DaVinci Resolve 的时间线中定位到该字幕的起始帧。 |
| `tree` | `itemDoubleClicked` | `on_item_double_clicked` | 当用户双击字幕内容列时，允许用户直接在表格中编辑字幕文本。 |
| `window` | `subtitleDataChanged` | `on_subtitle_data_changed` | 当字幕文本被编辑后，此信号被触发，调用 `SubtitleManager` 更新数据模型和缓存文件。 |
| `track_combo` | `currentIndexChanged` | `on_track_changed` | 当用户切换字幕轨道时，调用 `AppService` 加载新轨道的字幕数据并更新UI。 |
| `export_reimport_button` | `clicked` | `on_export_reimport_clicked` | 将当前在UI中的所有修改（包括未保存的）应用到 Resolve 的时间线中。 |
| `import_srt_button` | `clicked` | `on_import_srt_clicked` | 打开文件对话框，允许用户导入一个 `.srt` 文件来作为新的字幕数据源。 |
| `find_next_button` | `clicked` | `on_find_next_clicked` | 在字幕列表中查找下一个匹配 "Find" 文本框内容的项目。 |
| `replace_button` | `clicked` | `handle_replace_current` | 替换当前选中字幕中的匹配文本。 |
| `replace_all_button` | `clicked` | `handle_replace_all` | 在所有字幕中执行查找和替换操作。 |

### 2.3 事件处理（槽函数）

槽函数是 `ApplicationController` 的核心，它们定义了如何响应用户的具体操作。

- **`on_refresh_button_clicked()`**:
    1.  检查 `subtitle_manager.is_dirty` 标志，如果用户有未同步的修改，则弹出对话框提示用户确认。
    2.  调用 `app_service.refresh_timeline_info()` 从 Resolve 获取最新的时间线信息（如轨道数）。
    3.  如果出错，则调用 `show_error_message()` 显示错误。
    4.  成功后，清空并重新填充字幕轨道下拉框 (`track_combo`)。
    5.  自动触发 `on_track_changed` 以加载默认轨道的字幕。

- **`on_track_changed(index)`**:
    1.  调用 `app_service.change_active_track(track_index)` 来处理切换轨道的逻辑。
    2.  服务层会先保存当前轨道的修改，然后从 Resolve 导出新轨道的数据。
    3.  如果出错，显示错误信息。
    4.  成功后，调用 `window.populate_table()` 将返回的字幕数据填充到UI表格中。

- **`on_export_reimport_clicked()`**:
    1.  检查是否存在有效的字幕数据。
    2.  直接调用 `app_service.export_and_reimport_subtitles()`，该服务方法封装了所有逻辑：保存修改 -> 导出到 Resolve。
    3.  根据返回结果，显示成功或失败的消息框。

- **`on_item_clicked(item, column)`**:
    1.  从点击的 `item` 中获取字幕ID。
    2.  在 `subtitle_manager` 中查找对应的字幕对象以获取其 `start` 时间码。
    3.  调用 `resolve_integration.get_timecode_utils()` 获取时间码转换工具。
    4.  将时间码转换为帧数，再转换为 Resolve 可识别的 `HH:MM:SS:FF` 格式。
    5.  调用 `resolve_integration.timeline.SetCurrentTimecode()` 来移动时间线上的播放头。

- **`on_subtitle_data_changed(item_index, new_text)`**:
    1.  此槽函数接收由UI发出的 `subtitleDataChanged` 信号，其中包含已编辑字幕的索引和“干净”的文本（已去除HTML标签）。
    2.  调用 `subtitle_manager.update_subtitle_text()`，将新的文本更新到数据模型中，并自动将 `is_dirty` 标志设为 `True`。

- **`handle_replace_all()` / `handle_replace_current()`**:
    1.  从UI的输入框中获取查找和替换的文本。
    2.  调用 `app_service` 中对应的 `replace_all_subtitles` 或 `replace_current_subtitle` 方法。
    3.  `AppService` 进一步将请求委托给 `SubtitleManager` 来执行实际的文本替换逻辑。
    4.  控制器接收返回的变更列表，并调用 `window.update_all_items_for_replace()` 或 `window.update_item_for_replace()` 来更新UI，高亮显示变更。

- **`on_import_srt_clicked()`**:
    1.  如果存在未保存的修改，则提示用户确认。
    2.  调用 `app_service.import_srt_file()`，该服务会弹出文件选择对话框。
    3.  服务层读取文件内容，并委托 `SubtitleManager` 将SRT内容解析为标准的字幕数据结构。
    4.  如果解析成功，则调用 `window.populate_table()` 更新UI。

### 2.4 应用生命周期管理

- **`run()`**:
    1.  调用 `connect_signals()` 完成所有信号和槽的绑定。
    2.  调用 `self.window.show()` 显示主窗口。
    3.  调用 `sys.exit(self.app.exec())` 启动 Qt 的事件循环。这是应用的入口点，程序将在此处阻塞，直到应用退出。

- **`cleanup_on_exit()`**:
    1.  此方法被连接到 `app.aboutToQuit` 信号。
    2.  当应用关闭时，它会调用 `self.subtitle_manager.clear_cache()` 来删除在会话期间生成的临时 `.json` 缓存文件，保持项目目录的整洁。

## 3. 总结

`ApplicationController` 通过精心设计的信号与槽机制，成功地将复杂的UI交互逻辑与后端的业务处理和数据管理分离开来。它作为应用的中枢神经系统，确保了数据流在视图、服务和模型之间的顺畅流转，是整个应用能够协调工作的核心。