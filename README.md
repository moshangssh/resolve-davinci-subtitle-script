# Subvigator - Python Port

This project is a Python port of the "Andy's Subvigator" DaVinci Resolve script, originally written in Lua.

## Features

*   Filter and search subtitles in the current timeline.
*   Navigate the timeline by clicking on subtitles.
*   Combine multiple subtitles into a single entry for easier reading.

## Project Structure

```
.
├── Andys Subvigator.lua  (Original Script)
├── memory_bank/
├── README.md
└── src/
    ├── __init__.py
    ├── main.py
    ├── resolve_integration.py
    ├── subtitle_manager.py
    ├── timecode_utils.py
    └── ui.py




项目概述:
这是一个DaVinci Resolve的Python脚本，用于过滤、搜索和导航时间线上的字幕。

核心组件和流程:

启动 (main.py):

ApplicationController 被实例化。
它初始化 QApplication, ResolveIntegration, TimecodeUtils, 和 SubvigatorWindow (UI)。
它连接UI信号（如按钮点击、文本更改）到相应的控制器方法。
调用 run() 方法来显示UI并启动事件循环。

UI (ui.py):

SubvigatorWindow (一个 QMainWindow) 构建了用户界面。
UI包含一个搜索框、一个字幕树状视图、一个轨道选择器和一个刷新按钮。
populate_table 方法用从Resolve获取的字幕数据填充树状视图。
filter_tree 方法根据搜索框中的文本过滤树状视图中的字幕。

Resolve集成 (resolve_integration.py):

ResolveIntegration 类使用 fusionscript 或 DaVinciResolveScript 连接到DaVinci Resolve。
get_current_timeline_info() 获取帧率和字幕轨道数。
get_subtitles_with_timecode() 从时间线中检索字幕，并使用 TimecodeUtils 将它们的开始/结束帧转换为时间码。
set_active_subtitle_track() 启用/禁用特定的字幕轨道。

用户交互流程:

刷新: 用户点击“刷新”按钮。
refresh_data() 在 ApplicationController 中被调用。
它调用 resolve_integration.get_current_timeline_info()。
它用可用的字幕轨道更新轨道选择下拉菜单 (track_combo)。
它触发 on_track_changed 来为当前选定的轨道加载字幕。

选择轨道: 用户从 track_combo 中选择一个轨道。
on_track_changed() 被调用。
它调用 resolve_integration.get_subtitles_with_timecode() 来获取该轨道的字幕。
它调用 window.populate_table() 来用获取到的数据显示UI。

过滤字幕: 用户在搜索框中输入文本。
filter_subtitles() (在 ApplicationController 中) 或 filter_tree() (在 SubvigatorWindow 中) 被调用以隐藏不匹配的字幕。

点击字幕: 用户点击树状视图中的一个字幕项。
on_item_clicked() 被调用。
它获取字幕的起始帧。
它使用 timecode_utils 将帧转换为时间码。
它调用 resolve_integration.timeline.SetCurrentTimecode() 来在Resolve的时间线中导航到该时间码。