# Subvigator 代码审查与BUG分析报告

**报告生成时间:** 2025年7月13日
**审查员:** 💻 代码开发者 (AI Assistant)
**任务ID:** `81374f14-b564-4821-b6bf-fc1f3d40095a`

---

## 1. 概述

本次代码审查系统地分析了 `src` 目录下的所有Python代码，重点关注了数据一致性、错误处理、UI状态管理、边界条件和资源管理五个方面。审查发现了 **5** 个主要问题，这些问题涉及数据丢失风险、程序健壮性、代码效率和资源泄露。

以下是详细的BUG报告和修复建议。

---

## 2. 详细BUG报告

### BUG #1: 数据一致性 - 刷新操作导致静默的数据丢失

-   **严重性:** 高
-   **问题描述:** 当用户在UI中修改了字幕但未执行“导出并重导入”时，点击“刷新”按钮会触发 `resolve_integration.cache_all_subtitle_tracks()`，此操作会用DaVinci Resolve的实时数据强制覆盖本地缓存文件。这导致用户在UI上所做的任何修改都被**静默地丢弃**，没有给予任何警告或确认提示。
-   **相关文件和行号:**
    -   触发点: [`src/main.py:71`](src/main.py:71) (在 `on_refresh_button_clicked` 中调用 `cache_all_subtitle_tracks`)
-   **复现步骤:**
    1.  启动插件并加载一条字幕轨道。
    2.  在UI的字幕列表中，手动编辑任意一行的文本内容。
    3.  **不要**点击“导出并重导入”按钮。
    4.  点击“刷新”按钮。
    5.  **观察:** 刚刚编辑的文本内容消失，恢复为Resolve中的原始文本，数据丢失。
-   **修复建议:**
    1.  在 `SubtitleManager` 中引入一个“脏”状态标志（`is_dirty`），任何修改字幕的操作（如 `update_subtitle_text`, `handle_replace_all`）都会将此标志设为 `True`。当成功“导出并重导入”后，将标志设为 `False`。
    2.  在 `ApplicationController.on_refresh_button_clicked` 方法中，执行刷新前检查 `subtitle_manager.is_dirty` 状态。
    3.  如果为 `True`，则弹出一个 `QMessageBox` 警告用户：“您有未同步到 Resolve 的修改，刷新将丢弃这些修改。是否继续？”，给予用户选择的机会。

### BUG #2: 错误处理 - 关键API调用缺少异常捕获

-   **严重性:** 高
-   **问题描述:** 在 `resolve_integration.py` 中，多个直接与DaVinci Resolve API交互的函数（如 `get_current_timeline_info`, `get_subtitles`, `set_active_subtitle_track`）缺少 `try...except` 块。如果API调用因任何原因失败（如Resolve项目已关闭、时间线不存在、进程无响应），程序会直接崩溃或返回 `None`，导致上层UI无任何响应或错误提示，用户体验极差。
-   **相关文件和行号:**
    -   [`src/resolve_integration.py:84`](src/resolve_integration.py:84) (`get_current_timeline_info`)
    -   [`src/resolve_integration.py:92`](src/resolve_integration.py:92) (`get_subtitles`)
    -   [`src/resolve_integration.py:127`](src/resolve_integration.py:127) (`set_active_subtitle_track`)
-   **复现步骤（假设）:**
    1.  启动插件。
    2.  在DaVinci Resolve中，关闭当前项目。
    3.  点击插件UI上的“刷新”按钮。
    4.  **观察:** 插件无任何反应，但控制台可能会抛出未捕获的异常。
-   **修复建议:**
    1.  在 `resolve_integration.py` 中，为所有直接调用Resolve API的地方包裹 `try...except Exception as e:` 块。
    2.  修改这些函数的返回值，使其在成功时返回数据，在失败时返回一个包含错误信息的元组，例如 `(None, "Error: Could not get timeline.")`。
    3.  在 `main.py` 的调用处（如 `on_refresh_button_clicked`），检查返回结果。如果检测到错误，则使用 `QMessageBox` 向用户显示一个清晰、友好的错误提示。

### BUG #3: UI状态管理 - “全部替换”操作效率低下且存在风险

-   **严重性:** 中
-   **问题描述:** 在 `handle_replace_all` 流程中，数据同步的实现方式存在问题。它首先在 `SubtitleManager` 中执行一次全局替换并**写入文件**，然后又从UI (`get_all_subtitles_data`) **回读所有数据**，再交给 `SubtitleManager` **第二次写入文件**。
-   **相关文件和行号:**
    -   [`src/main.py:162-169`](src/main.py:162-169)
-   **问题分析:**
    1.  **效率低下:** 同样的操作导致了两次完整的数据写入，造成不必要的I/O开销。
    2.  **设计模式风险:** “从UI回读数据再覆盖后端”的模式是危险的，它打破了 `Model -> View` 的单向数据流原则。如果UI的 `get_all_subtitles_data` 方法未来出现BUG，可能会导致后端数据被污染。
-   **修复建议:**
    1.  修改 `subtitle_manager.handle_replace_all` 方法，使其只在内存中更新 `self.subtitles_data` 并返回 `changes` 列表，**移除**内部的 `_save_changes_to_json()` 调用。
    2.  修改 `main.py` 中的 `handle_replace_all` 方法。在收到 `changes` 列表并更新UI后，只需调用一次 `self.subtitle_manager._save_changes_to_json()` 即可，无需再从UI回读数据。

### BUG #4: 边界条件 - 时间码工具函数对无效输入处理不当

-   **严重性:** 中
-   **问题描述:** `timecode_utils.py` 中的几个核心函数在面对无效或极端输入时，缺乏足够的保护措施。
-   **相关文件和行号及具体问题:**
    1.  [`src/timecode_utils.py:145`](src/timecode_utils.py:145) (`timecode_to_srt_format`): 传入负数 `frame` 会返回格式错误的负数时间码。
    2.  [`src/timecode_utils.py:111`](src/timecode_utils.py:111) (`timecode_from_frame`): 传入负数 `frame` 会导致底层C库行为未定义。
    3.  [`src/timecode_utils.py:100`](src/timecode_utils.py:100) (`frame_from_timecode`): 对格式错误的 `timecode` 字符串抛出的是通用的 `RuntimeError`，信息不明确。
    4.  [`src/timecode_utils.py:86`](src/timecode_utils.py:86) (`get_fraction`): 对非数字字符串的 `frame_rate` 输入会导致程序因 `float()` 转换失败而直接崩溃。
-   **修复建议:**
    1.  对于 `timecode_to_srt_format` 和 `timecode_from_frame`，在函数开头添加 `frame = max(0, frame)`，确保帧数不为负。
    2.  对于 `frame_from_timecode`，将 `RuntimeError` 包装成一个更具体的 `ValueError`，并提供更清晰的错误信息。
    3.  对于 `get_fraction`，在函数开头用 `try...except ValueError` 包裹 `float()` 转换，并抛出带有更清晰描述的 `ValueError`。

### BUG #5: 资源管理 - 轨道缓存文件从未被清理

-   **严重性:** 低
-   **问题描述:** 插件会在系统的临时目录下创建一个 `subvigator_cache` 目录，用于存放每个轨道的JSON缓存。但代码中没有任何逻辑来清理这个目录。这会导致用户的临时文件夹中不断累积来自不同项目的、已无用的缓存文件，造成磁盘空间泄露。
-   **相关文件和行号:**
    -   缓存目录定义: [`src/subtitle_manager.py:15`](src/subtitle_manager.py:15)
    -   缓存文件创建: [`src/resolve_integration.py:155`](src/resolve_integration.py:155)
-   **修复建议:**
    在 `ApplicationController` 中捕获 `QApplication.aboutToQuit` 信号。当信号触发时（即应用关闭前），调用一个新创建的 `subtitle_manager.clear_cache()` 方法。该方法使用 `shutil.rmtree()` 来安全地、递归地删除整个 `subvigator_cache` 目录，确保每次会话结束后不留任何痕迹。