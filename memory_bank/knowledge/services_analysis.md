# AppService 技术文档

本文档旨在详细分析 `AppService` 类的技术实现，包括其作为门面（Facade）模式的应用、公共接口的业务逻辑、以及依赖注入（Dependency Injection）的使用。

## 1. 核心职责与设计模式

`AppService` 在整个应用架构中扮演着至关重要的 **服务层** 和 **协调者** 角色。它完美地实现了 **门面（Facade）设计模式**。

### 1.1. 门面模式 (Facade Pattern)

`AppService` 为复杂的子系统（`resolve_integration` 和 `subtitle_manager`）提供了一个统一、简化的接口。上层调用者，即 [`src/main.py`](src/main.py:1) 中的 `ApplicationController`，只需要与 `AppService` 交互，而无需关心底层模块的实现细节。

*   **简化调用**: `ApplicationController` 无需知道如何操作DaVinci Resolve的API，也无需管理字幕数据的缓存和读写，只需调用 `app_service.export_and_reimport_subtitles()` 这样的高级接口。
*   **降低耦合**: UI控制层 (`ApplicationController`) 与业务逻辑层 (`resolve_integration`, `subtitle_manager`) 实现了解耦。如果未来底层API或缓存策略发生变化，只需要修改 `AppService` 内部的实现，而 `ApplicationController` 的代码基本不受影响。

### 1.2. 依赖注入 (Dependency Injection)

在 `AppService` 的 `__init__` 方法中，它接收 `ResolveIntegration` 和 `SubtitleManager` 的实例作为参数，而不是在内部创建它们。

```python
# src/services.py

class AppService:
    def __init__(self, resolve_integration: ResolveIntegration, subtitle_manager: SubtitleManager):
        self.resolve_integration = resolve_integration
        self.subtitle_manager = subtitle_manager
```

这种模式带来了以下好处：
*   **可测试性**: 在单元测试中，可以轻松地为 `AppService` 注入模拟（Mock）的 `resolve_integration` 和 `subtitle_manager` 对象，从而在不依赖DaVinci Resolve实际环境的情况下测试其协调逻辑。
*   **灵活性**: 依赖关系由外部（在 [`main.py`](src/main.py:1) 中）组装，使得更换或扩展底层实现变得更加容易。

## 2. 公共方法分析

以下是对 `AppService` 每个公共方法的详细拆解。

### `export_and_reimport_subtitles()`

*   **业务目标**: 响应用户点击“导出/再导入”按钮的操作。核心目标是将当前（可能已编辑）的字幕数据重新应用到DaVinci Resolve的一条新轨道上，实现“保存”或“应用更改”的效果。
*   **协调流程**:
    1.  检查 `subtitle_manager.is_dirty` 标志。如果为 `True`，表示有未保存的修改。
    2.  调用 `subtitle_manager._save_changes_to_json()`，将内存中的字幕修改持久化到本地的JSON缓存文件。
    3.  调用 `resolve_integration.reimport_from_json_file()`，并传入缓存文件的路径。`resolve_integration` 模块会负责读取JSON，将其转换为SRT格式，导入Resolve的媒体池，并最终添加到时间线的新轨道上。
    4.  操作成功后，将 `subtitle_manager.is_dirty` 重置为 `False`，因为更改已同步。
*   **返回值**: 返回一个元组 `(bool, str)`。`ApplicationController` 根据布尔值判断操作是否成功，并使用字符串向用户显示提示信息（成功或失败）。

### `change_active_track(track_index)`

*   **业务目标**: 响应用户在UI界面上切换字幕轨道的操作。
*   **协调流程**:
    1.  首先检查并保存当前轨道的未决修改（通过调用 `subtitle_manager._save_changes_to_json()`）。
    2.  调用 `resolve_integration.set_active_subtitle_track(track_index)`，通知DaVinci Resolve在时间线上启用新的目标轨道。
    3.  调用 `subtitle_manager.load_subtitles(track_index)`。此方法会首先检查本地是否存在该轨道的缓存（JSON文件），如果存在则直接加载；如果不存在（缓存未命中），则会调用 `resolve_integration` 从Resolve中导出该轨道的字幕数据，并创建缓存文件。
*   **返回值**: 返回一个元组 `(subtitles, error_message)`。`subtitles` 是包含字幕数据的列表，`ApplicationController` 用它来刷新UI中的字幕表格。

### `refresh_timeline_info()`

*   **业务目标**: 响应用户点击“刷新”按钮，获取DaVinci Resolve时间线的最新信息（如字幕轨道数量）。
*   **协调流程**: 这是一个简单的直通（pass-through）调用。它直接调用 `resolve_integration.get_current_timeline_info()` 并返回结果。此过程不涉及 `subtitle_manager`。
*   **返回值**: 返回一个元组 `(timeline_info, error_message)`。`ApplicationController` 使用返回的 `timeline_info` 字典来更新UI中的轨道选择下拉框。

### `replace_current_subtitle(item_index, find_text, replace_text)`

*   **业务目标**: 响应用户对单个选定字幕条目执行“替换”操作。
*   **协调流程**: 此操作纯粹是数据处理，因此只与 `subtitle_manager` 交互。
    1.  调用 `subtitle_manager.handle_replace_current()` 来执行单条字幕的文本替换。
    2.  `subtitle_manager` 内部会更新内存中的数据，并标记 `is_dirty = True`，然后保存到JSON缓存。
*   **返回值**: 返回一个包含变更详情的字典 `{'index': ..., 'old': ..., 'new': ...}`。`ApplicationController` 用它来精确更新UI表格中的对应行。

### `replace_all_subtitles(find_text, replace_text)`

*   **业务目标**: 响应用户执行“全部替换”操作。
*   **协调流程**:
    1.  调用 `subtitle_manager.handle_replace_all()`，该方法会遍历所有字幕并执行文本替换。
    2.  如果发生了任何替换，`subtitle_manager` 内部会保存所有更改到JSON缓存文件。
*   **返回值**: 返回一个包含所有变更详情的列表 `[change1, change2, ...]`。`ApplicationController` 用它来批量更新UI表格。

### `import_srt_file(parent_widget)`

*   **业务目标**: 响应用户点击“导入SRT”按钮，允许从外部SRT文件加载字幕数据。
*   **协调流程**:
    1.  使用 `QFileDialog` 弹出文件选择对话框让用户选择文件。
    2.  读取SRT文件的内容。
    3.  调用 `subtitle_manager.load_subtitles_from_srt_content()`。该方法会：
        a.  使用 `format_converter` 将SRT文本内容解析为标准的JSON格式。
        b.  用解析出的数据替换内存中的 `subtitles_data`。
        c.  将 `is_dirty` 设为 `True`。
        d.  将新的字幕数据保存到一个特殊的缓存文件 `imported_srt.json` 中。
*   **返回值**: 返回一个元组 `(subtitles, error_message)`。`ApplicationController` 用返回的 `subtitles` 数据来填充UI表格。
