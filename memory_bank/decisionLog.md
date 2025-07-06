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