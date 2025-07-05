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