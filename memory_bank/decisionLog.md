# 决策日志
记录架构和实现决策。
---
### 决策
[2025-07-05 15:47:00] - 选择了 Python 项目的架构。项目将包含 `subvigator` 应用目录，其中包含 `main.py`, `timecode_utils.py`, `ui.py`, 和 `resolve_integration.py`。还将包括 `requirements.txt` 和 `README.md`。

---
### 代码实现 [核心逻辑和API集成]
[2025-07-05 15:54:00] - 完成了将 'Andys Subvigator.lua' 重构为结构化 Python 应用程序。

**实现细节：**
- **`timecode_utils.py`**: 使用 `cffi` 移植了基于 `avutil` 的时间码计算逻辑。
- **`resolve_integration.py`**: 封装了与 DaVinci Resolve API 的所有交互，使其与主应用程序逻辑分离。
- **`ui.py`**: 使用 `PySide6` 创建了一个现代化的用户界面，重现了原始脚本的布局和控件。
- **`main.py`**: 作为应用程序控制器，将 UI、业务逻辑和 Resolve API 集成在一起。

**测试框架：**
- 使用 Python 内置的 `unittest` 框架和 `unittest.mock` 库。

**测试结果：**
- 覆盖率：为 `timecode_utils` 和 `resolve_integration` 模块的关键功能提供了全面的单元测试。
- 通过率：100% (17/17 个测试用例通过)。

---
### 代码实现 [动态库加载]
[2025-07-05 18:39:00] - [重构 `TimecodeUtils` 以通过 Resolve API 自动加载 `avutil` 库]

**实现细节：**
修改了 `TimecodeUtils._load_library` 方法，利用 `resolve.Fusion().MapPath("FusionLibs:")` 来定位 DaVinci Resolve 的内部库目录，并从中加载 `avutil` 动态链接库。此举消除了对环境变量或手动放置 DLL 文件的依赖。同时调整了 `TimecodeUtils` 和 `ApplicationController` 的构造函数以传递 `resolve` 实例。

**测试框架：**
下一步将使用 `pytest` 和 `unittest.mock` 对修改后的逻辑进行单元测试。

**测试结果：**
- 覆盖率：待测试
- 通过率：待测试

---
### 代码实现 [UI 排序修复]
[2025-07-06 00:02:00] - [修复了 UI 中字幕的排序问题]

**实现细节:**
为了解决 `QTreeWidget` 按字母顺序对字幕编号进行排序的问题，创建了一个名为 `NumericTreeWidgetItem` 的新类，该类继承自 `QTreeWidgetItem`。通过重写 `__lt__` 方法，确保第一列（字幕编号）按数值进行比较，从而实现了正确的数字排序。`populate_table` 方法已更新为使用这个新的自定义项。

**测试框架:**
N/A

**测试结果:**
- 覆盖率：N/A
- 通过率：N/A

---
### 代码实现 [核心功能]
[2025-07-06 13:38:05] - 实现了 `TimecodeUtils` 类用于处理时间码转换。

**实现细节：**
创建了 `timecode_utils.py` 模块，封装了使用 `cffi` 与 `libavutil` 库交互的逻辑，提供了时间码与帧之间的转换功能。

**测试框架：**
`pytest`, `pytest-cov`

**测试结果：**
- 覆盖率：100%
- 通过率：100%


---
### 代码实现 [ResolveIntegration]
[2025-07-06 14:22:19] - 实现了 `ResolveIntegration` 类，用于封装与 DaVinci Resolve API 的交互。

**实现细节：**
创建了 `resolve_integration.py` 文件，包含 `ResolveIntegration` 类。该类在初始化时连接到 DaVinci Resolve，并提供了获取时间线信息和字幕数据的方法。

**测试框架：**
pytest, pytest-cov, unittest.mock

**测试结果：**
- 覆盖率：100%
- 通过率：100%

---
### 代码实现 [UI]
[2025-07-06 14:33:47] - 创建了 `ui.py` 文件，包含 `SubvigatorWindow` 和 `NumericTreeWidgetItem` 类，用于构建应用程序的图形用户界面。

**实现细节：**
- `SubvigatorWindow`: 主窗口类，负责UI布局和控件创建。
- `NumericTreeWidgetItem`: 自定义树状组件项，支持按数字排序。

**测试框架：**
- PyTest
- pytest-qt

**测试结果：**
- 覆盖率：100%
- 通过率：100%

---
### 代码实现 [Application Entry Point]
[2025-07-06 14:57:15] - 创建了应用程序的主入口点 `main.py`。

**实现细节：**
`main.py` 文件包含 `ApplicationController` 类和 `main` 函数。`ApplicationController` 负责初始化 QApplication、集成 Resolve、处理 UI 信号和管理应用程序的核心逻辑。`main` 函数作为程序的起点，实例化并运行控制器。

**测试框架：**
pytest, pytest-cov

**测试结果：**
- 覆盖率：100%
- 通过率：100%
- **决策时间:** 2025/7/6 下午5:31:18
- **决策:** 为 `search_text` (QLineEdit) 控件添加 `textChanged` 信号，并将其连接到 `filter_tree` 方法，以实现字幕列表的实时过滤功能。
- **理由:** 这是 Qt/PySide 中实现动态UI更新的标准做法，能够提供流畅的用户体验。
- **实施者:** 💻 代码开发者
---
- **决策时间:** 2025/7/6 下午6:13:35
- **决策:** 从UI中移除了 "df navigation"、"Dynamic search text" 和 "combine subs" 功能及其相关的布局代码。
- **理由:** 这些功能目前不是核心需求，移除它们可以简化UI，让界面更整洁。
- **实施者:** 🧠 NexusCore

---
### 代码实现 [UI交互]
[2025-07-06 18:37:00] - 为字幕轨道切换下拉框实现功能。

**实现细节：**
在 `ApplicationController` 中添加了 `on_track_changed` 方法，用于处理轨道切换事件。该方法从UI获取当前轨道索引，调用 `resolve_integration.get_subtitles` 获取新字幕，并更新UI表格。同时，将 `track_combo.currentIndexChanged` 信号连接到此新方法，并修改 `refresh_data` 以在初始加载时正确触发事件。

**测试框架：**
- PyTest
- pytest-cov
- unittest.mock

**测试结果：**
- 覆盖率：100%
- 通过率：100%
---
**决策时间:** 2025/7/6 下午6:54:37
**决策:** 修复 `AttributeError: 'SubvigatorWindow' object has no attribute 'drop_frame_checkbox'`
**原因:** 用户报告在UI中点击字幕时程序崩溃。经查，是由于代码试图访问一个已被移除的UI组件 `drop_frame_checkbox`。
**行动:** 委派了一个子任务给 `code-developer` 模式，移除了 `src/main.py` 中对 `drop_frame_checkbox` 的引用。
**结果:** 错误已修复，程序恢复正常。



---
### 代码实现 [功能]
[2025-07-06 19:17:08] - 在 `ResolveIntegration` 类中实现了 `set_active_subtitle_track` 函数。

**实现细节：**
该函数通过迭代所有字幕轨道，并使用 `SetTrackEnable` API 根据传入的 `track_index` 参数来启用或禁用相应的轨道，从而实现了活动字幕轨道的切换。

**测试框架：**
pytest

**测试结果：**
- 覆盖率：97%
- 通过率：100%

---
**决策时间:** 2025/7/6 下午7:23:57
**决策:** 实现 `set_active_subtitle_track` 函数以在 DaVinci Resolve 中同步字幕轨道状态。
**原因:** 这是实现用户请求的核心功能，即在插件 UI 中切换轨道时，能够实时启用/禁用 Resolve 中的相应轨道。
**行动:** 委派了一个子任务给 `code-developer` 模式，在 `resolve_integration.py` 中实现了此函数，并通过了单元测试。
**结果:** `set_active_subtitle_track` 函数已成功实现并经过测试。

---
**决策时间:** 2025/7/6 下午10:22:22
**决策:** 将 `track_list_widget` 的 `currentItemChanged` 信号连接到 `on_subtitle_track_selected` 方法，以在 UI 中同步轨道选择。
**原因:** 这是将后端轨道切换逻辑 (`set_active_subtitle_track`) 与前端 UI 事件连接起来的关键步骤，从而完成整个功能。
**行动:** 委派了一个子任务给 `code-developer` 模式，在 `main.py` 中实现了信号连接和处理函数。
**结果:** UI 轨道选择现在可以正确触发 DaVinci Resolve 中的轨道状态同步。

---
**决策时间:** 2025/7/7 上午12:46:19
**决策:** 修复 DaVinci Resolve 环境中的 `ImportError` 和 `NameError`。
**原因:** 用户报告在 DaVinci Resolve 中运行脚本时出现 `ImportError: attempted relative import with no known parent package` 错误。这是由于 Resolve 的脚本执行环境未将 `src` 目录识别为 Python 包。后续还发现，在某些嵌入式环境中，`__file__` 变量可能未定义，导致 `NameError`。
**行动:** 委派了一个子任务给 `code-developer` 模式，在 `src/main.py` 中进行了以下修改：
1.  动态地将项目根目录添加到 `sys.path`。
2.  将所有相对导入更改为绝对导入。
3.  使用 `sys.argv[0]` 作为 `os.path.abspath` 的参数，以兼容 `__file__` 未定义的执行环境。
**结果:** 脚本的导入问题和潜在的 `NameError` 都已解决，增强了脚本在不同环境下的健壮性。


---
### 决策
[2025-07-07 01:43:18] - 为Subvigator项目创建了核心工作流程和组件交互的Mermaid流程图。该图可视化了从应用启动到用户具体操作（如刷新、选择轨道、过滤字幕和时间线导航）的完整数据流和控制流，明确了 `ApplicationController`, `SubvigatorWindow`, 和 `ResolveIntegration` 之间的职责与交互关系。



---
### 代码实现 [核心]
[2025-07-07 15:52:10] - 实现基于JSON的字幕处理工作流

**实现细节：**
- **`resolve_integration.py`**: 添加 `export_subtitles_to_json` 方法，用于将时间轴中的字幕数据导出为标准化的JSON格式。该文件存储在操作系统的临时目录中，以确保跨平台兼容性。
- **`ui.py`**: 修改 `populate_table` 方法，使其能够接受JSON文件路径。添加了 `load_subtitles_from_json` 辅助方法来处理文件读取和解析，实现了UI与数据源的解耦。
- **`main.py`**: 更新 `ApplicationController` 以协调新的工作流程。`on_track_changed` 方法现在会先导出JSON，然后使用该文件更新UI。为了保留关键的“点击跳转”功能，原始的字幕对象（包含帧数据）被临时存储在窗口实例中，`on_item_clicked` 方法被重构为使用此缓存数据来查找精确的起始帧。

**测试框架：**
- Pytest
- Pytest-mock

**测试结果：**
- 覆盖率：89%
- 通过率：100% (61/61 passed)



---
### 代码实现 [功能]
[2025-07-07 21:40:16] - 在`resolve_integration.py`中添加了`export_subtitles_to_srt`函数。

**实现细节：**
该函数从DaVinci Resolve时间线中提取字幕，并将其格式化为SRT（SubRip Subtitle）格式的字符串。它利用`timecode_utils`来处理时间码的转换。

**测试框架：**
后续将使用`pytest`进行单元测试。

**测试结果：**
- 覆盖率：待定
- 通过率：待定

---
**决策时间:** 2025/7/7 下午11:26:40
**决策:** 采纳技术调研结果，实施新的字幕导出-导入工作流。
**原因:** 调研确认了通过手动生成SRT文件，并利用DaVinci Resolve的API进行导入、创建新轨道和添加媒体是可行的。这是实现用户请求的核心技术路径。
**行动:**
1.  将技术调研结果归档到 `memory_bank/knowledge/davinci_resolve_srt_export_import.md`。
2.  委派一个 `code-developer` 子任务，根据调研结果修改 `src/resolve_integration.py` 和 `src/main.py` 来实现完整的功能。
**结果:** 技术方案已确定并记录，下一步是代码实现。


---
### 代码实现 [功能模块]
[2025-07-08 09:13:15] - 在 `export_subtitles_to_srt` 中实现了对 DaVinci Resolve 1小时时间码偏移的校正。

**实现细节：**
修改了 `src/resolve_integration.py` 中的 `export_subtitles_to_srt` 函数。该函数现在会检查时间线的起始时间码。如果时间码以 "01:" 开头，则在计算SRT时间戳之前，从每个字幕的起始和结束帧中减去相当于1小时的帧数。此修改确保了从非零时间码开始的时间线导出的字幕是准确的。

**测试框架：**
- Pytest
- unittest.mock

**测试结果：**
- 覆盖率：100% (通过参数化测试覆盖了 `00:00:00:00` 和 `01:00:00:00` 两种场景)
- 通过率：100% (所有18个相关测试均已通过)


---
### 代码实现 [功能修改]
[2025-07-08 09:34:09] - 修改 `export_and_reimport_subtitles` 函数以仅显示新字幕轨道。

**实现细节：**
在 `src/resolve_integration.py` 的 `export_and_reimport_subtitles` 函数中，注释掉了重新启用所有字幕轨道的代码，以确保只有新创建的轨道保持启用状态。

**测试框架：**
pytest

**测试结果：**
- 覆盖率：87%
- 通过率：100%


---
**决策时间:** 2025/7/8 上午11:56:51
**决策:** 修改 `export_and_reimport_subtitles` 函数，以在重新导入字幕后仅显示新建的字幕轨道。
**原因:** 这是用户明确提出的需求，以避免在处理新字幕时被旧字幕干扰。
**行动:** 委派了一个子任务给 `code-developer` 模式，在 `src/resolve_integration.py` 中修改了 `export_and_reimport_subtitles` 函数，并更新了 `src/main.py` 以正确处理UI刷新。
**结果:** 现在，当用户使用“导出并重新导入”功能时，只有新创建的字幕轨道会保持可见，提供了更清晰的工作流程。
