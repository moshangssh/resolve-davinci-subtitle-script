# UI 层 API 使用情况分析报告

本文档旨在详细分析 `src/ui.py` 和 `src/ui_logic.py` 文件，明确 UI 层如何利用 Qt (PySide6) 和 `difflib` API 来构建用户界面和实现核心交互功能。

## 1. Qt (PySide6) API 使用分析 (`ui.py`)

`ui.py` 文件作为应用的视图层，负责界面的构建、布局和基础事件响应。它使用 PySide6 框架的各种组件来创建丰富的用户体验。

### 1.1. 关键组件识别

在 `SubvigatorWindow` 类中，主要使用了以下 Qt 组件：

*   **`QMainWindow`**: 作为应用的主窗口容器。
*   **`QTreeWidget`**: 核心组件，用于以表格形式展示字幕列表。它被配置为拥有6个列（'#', '长度', '字幕', '入点', '出点', '开始帧'）。
*   **`InspectorPanel` (自定义 `QWidget`)**: 这是一个自定义的侧边栏面板，内部封装了多个标准 Qt 组件，包括：
    *   `QLineEdit` (`search_text`, `find_text`, `replace_text`): 用于文本输入，如搜索和替换。
    *   `QPushButton` (`find_next_button`, `replace_all_button`): 用于触发查找和替换操作。
    *   `QComboBox` (`search_type_combo`): 提供不同的搜索模式（包含、精确等）。
*   **`QHeaderView`**: 用于配置 `QTreeWidget` 的表头行为，如列宽的调整策略（`ResizeToContents`, `Stretch`）。

### 1.2. 布局管理

窗口的整体布局通过以下 Qt 布局管理器实现：

*   **`QHBoxLayout`**: 作为主布局 (`main_layout`)，将中央窗口部件水平划分为两个主要区域。
*   **空间分配**: `main_layout` 使用 `addWidget(widget, stretch_factor)` 将空间按比例分配：
    *   `self.tree` (QTreeWidget) 分配了 `2` 的拉伸因子，占据了大约 2/3 的宽度。
    *   `self.inspector` (InspectorPanel) 分配了 `1` 的拉伸因子，占据了大约 1/3 的宽度。
*   这种布局方式清晰地将字幕列表和操作面板分离开来，提供了直观的用户界面。

### 1.3. 自定义委托 (Delegates)

为了自定义 `QTreeWidget` 中特定列的渲染和行为，项目利用了 `QStyledItemDelegate` 的子类。这些委托在 [`src/ui_components.py`](src/ui_components.py) 中定义，并在 [`src/ui.py:86-92`](src/ui.py:86) 处实例化和应用。

*   **`HtmlDelegate`**:
    *   **作用**: 此委托用于渲染包含 HTML 标签的富文本。它被应用于“#”、“字幕”、“入点”和“出点”列。
    *   **实现**: 它通过重写 `paint` 方法，并使用 `QTextDocument` 来解析和绘制 HTML 字符串。这使得字幕列可以高亮显示文本差异（例如，用红色删除线表示删除，用蓝色表示替换）。通过在 `setEditorData` 中提供纯文本，确保了编辑时看到的是干净的内容。
    *   **关键 API**: `QTextDocument.setHtml()`, `QTextDocument.drawContents()`。

*   **`CharCountDelegate`**:
    *   **作用**: 此委托应用于“长度”列，用于可视化显示字幕的字符数。
    *   **实现**: 它重写 `paint` 方法，不显示原始的数字文本，而是绘制一个彩色的圆形。圆的颜色根据字符数（`<= 15` 为绿色，`> 15` 为红色）动态变化，圆内居中显示字符数。这提供了一种比纯文本更直观的视觉反馈。
    *   **关键 API**: `QPainter.drawEllipse()`, `QPainter.drawText()`。

### 1.4. 信号与槽机制

应用的核心交互逻辑由 Qt 的信号与槽机制驱动：

*   **`itemChanged` 信号**: `self.tree.itemChanged.connect(self.on_subtitle_edited)` ([`src/ui.py:107`](src/ui.py:107))。当用户编辑并完成一个单元格的修改时，此信号被发射，并调用 `on_subtitle_edited` 槽函数。该槽函数接着调用 `ui_logic.handle_subtitle_edited` 来处理差异计算和HTML生成。
*   **`textChanged` 信号**: 检查器面板中的 `search_text` 和 `find_text` 输入框的 `textChanged` 信号被连接到 `filter_tree` 槽函数 ([`src/ui.py:110-111`](src/ui.py:110))，实现了对字幕列表的实时过滤。
*   **`clicked` 信号**: 按钮的 `clicked` 信号被连接到相应的槽函数以执行操作，例如查找下一个、全部替换等。
*   **`subtitleDataChanged` 自定义信号**: 这是一个在 `SubvigatorWindow` 中定义的自定义信号 ([`src/ui.py:35`](src/ui.py:35))。当字幕的纯文本内容被用户修改后，在 `on_subtitle_edited` 方法中通过 `self.subtitleDataChanged.emit(...)` 发射，用于通知其他组件（如控制器）数据已发生变化。

## 2. `difflib` API 使用分析 (`ui_logic.py`)

`ui_logic.py` 文件作为 UI 的逻辑层，封装了与视图无关的复杂交互逻辑，其中最核心的是文本比较和差异高亮显示，这是通过 Python 的 `difflib` 库实现的。

### 2.1. 核心函数

核心功能被封装在 `_generate_diff_html` 函数中 ([`src/ui_logic.py:6`](src/ui_logic.py:6))。

### 2.2. API 调用

该函数的核心是对 `difflib.SequenceMatcher` 的使用：

```python
s = difflib.SequenceMatcher(None, original_text, new_text)
opcodes = s.get_opcodes()
```

*   `difflib.SequenceMatcher` 类被实例化，用于比较两个字符串：`original_text`（修改前的文本）和 `new_text`（修改后的文本）。

### 2.3. 功能描述

*   **`get_opcodes()`**: 此方法返回一个操作码（opcode）列表。每个操作码是一个描述如何将原始字符串转换为新字符串的指令元组 `(tag, i1, i2, j1, j2)`。
    *   `tag`: 一个字符串，表示操作类型。
    *   `i1`, `i2`: 原始字符串中的切片索引。
    *   `j1`, `j2`: 新字符串中的切片索引。

*   **操作码处理**: 代码遍历 `get_opcodes()` 返回的列表，并根据 `tag` 的值构建一个 HTML 字符串：
    *   **`'equal'`**: 表示两段文本相同。代码直接将新文本的相应部分附加到结果字符串。
    *   **`'replace'`**: 表示一段文本被替换。代码使用 `style_config` 中定义的样式，将原始文本（`original_text[i1:i2]`）包裹在删除标签（如 `<font color="red"><s>...</s></font>`）中，并将新文本（`new_text[j1:j2]`）包裹在替换标签（如 `<font color="blue">...</font>`）中。
    *   **`'delete'`**: 表示一段文本被删除。代码将原始文本的相应部分包裹在删除标签中。
    *   **`'insert'`**: 表示一段文本被插入。代码将新文本的相应部分包裹在插入/替换标签中。

最终生成的 HTML 字符串被返回给 `ui.py`，并通过 `HtmlDelegate` 渲染在 `QTreeWidget` 中，从而实现了对文本差异的富文本高亮显示。

## 3. 总结模块功能

*   **`ui.py` (视图层)**:
    *   **职责**: 负责界面的构建、布局、样式加载和基础事件响应。
    *   **实现**: 使用 PySide6 的标准组件和布局管理器创建窗口结构，并通过自定义委托（`HtmlDelegate`, `CharCountDelegate`）增强 `QTreeWidget` 的视觉表现力。它通过信号与槽机制捕捉用户输入，并将复杂的逻辑处理请求转发给 `ui_logic`。

*   **`ui_logic.py` (逻辑层)**:
    *   **职责**: 封装了与视图无关的、可重用的 UI 交互逻辑。
    *   **实现**: 实现了如文本过滤、查找、以及最核心的基于 `difflib` 的文本差异比较和差异高亮HTML的生成。函数接受来自视图层的数据（如 `QTreeWidget` 的 item），执行计算，并返回处理结果（如 HTML 字符串或过滤后的数据）。

这种**逻辑与视图分离**的设计原则使得代码更加清晰、可维护和可测试。`ui.py` 关注“看起来怎么样”，而 `ui_logic.py` 关注“如何工作”，两者通过定义清晰的函数接口进行协作。