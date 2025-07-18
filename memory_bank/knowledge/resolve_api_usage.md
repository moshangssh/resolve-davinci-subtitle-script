# DaVinci Resolve API 调用分析报告 for `resolve_integration.py`

## 1. Resolve API 调用识别与用途分析

### `Resolve` 对象

*   **API 方法名:** `resolve.GetProjectManager()`
    *   **功能描述:** 获取项目管理器对象，它是访问 Resolve 中所有项目的入口点。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个 `ProjectManager` 对象，用于后续获取当前项目。

### `ProjectManager` 对象

*   **API 方法名:** `project_manager.GetCurrentProject()`
    *   **功能描述:** 获取当前在 DaVinci Resolve 中打开并处于活动状态的项目。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个 `Project` 对象，代表当前项目，用于访问时间线、媒体池等项目相关内容。

### `Project` 对象

*   **API 方法名:** `project.GetCurrentTimeline()`
    *   **功能描述:** 获取当前项目中的活动时间线。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个 `Timeline` 对象，用于对当前时间线进行操作，如获取/设置字幕、轨道等。
*   **API 方法名:** `project.GetMediaPool()`
    *   **功能描述:** 获取项目的媒体池对象。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个 `MediaPool` 对象，用于管理项目中的媒体文件，如此处用于导入 SRT 字幕文件。

### `Timeline` 对象

*   **API 方法名:** `timeline.GetSetting('timelineFrameRate')`
    *   **功能描述:** 获取当前时间线的帧率设置。
    *   **关键参数:** `'timelineFrameRate'` (字符串，指定要获取的设置项)
    *   **返回值及其用途:** 返回一个浮点数，表示时间线的帧率（例如 `24.0`, `29.97`）。该值在时间码和帧数之间转换时至关重要。
*   **API 方法名:** `timeline.GetTrackCount('subtitle')`
    *   **功能描述:** 获取时间线上指定类型轨道的数量。
    *   **关键参数:** `'subtitle'` (字符串，指定轨道类型为字幕)
    *   **返回值及其用途:** 返回一个整数，表示字幕轨道的总数。用于验证轨道索引是否有效。
*   **API 方法名:** `timeline.GetItemListInTrack('subtitle', track_number)`
    *   **功能描述:** 获取指定字幕轨道上的所有片段（即单个字幕条目）的列表。
    *   **关键参数:**
        *   `'subtitle'`: 指定轨道类型。
        *   `track_number`: (整数) 指定要从中获取字幕的轨道号（从 1 开始）。
    *   **返回值及其用途:** 返回一个包含 `TimelineItem` 对象的列表。插件遍历此列表以提取每个字幕的内容和时间信息。
*   **API 方法名:** `timeline.SetTrackEnable("subtitle", i, i == track_index)`
    *   **功能描述:** 启用或禁用指定的字幕轨道。
    *   **关键参数:**
        *   `"subtitle"`: 轨道类型。
        *   `i`: (整数) 轨道索引。
        *   `i == track_index`: (布尔值) 决定是启用 (`True`) 还是禁用 (`False`) 该轨道。
    *   **返回值及其用途:** 用于实现激活单个字幕轨道的功能，确保只有一个轨道处于活动状态。
*   **API 方法名:** `timeline.GetStartTimecode()`
    *   **功能描述:** 获取时间线的起始时间码。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个字符串，格式为 `"HH:MM:SS:FF"`。用于判断时间线是否从一小时标记（`01:00:00:00`）开始，以进行正确的时间码计算。
*   **API 方法名:** `timeline.GetStartFrame()`
    *   **功能描述:** 获取时间线的起始帧号。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个整数，表示时间线的起始总帧数。用于在需要基于零的计算时作为偏移量。
*   **API 方法名:** `timeline.AddTrack("subtitle")`
    *   **功能描述:** 在时间线上添加一个新的字幕轨道。
    *   **关键参数:** `"subtitle"`
    *   **返回值及其用途:** 用于在重新导入字幕时创建一个隔离的新轨道，避免与现有字幕冲突。
*   **API 方法名:** `timeline.SetCurrentTimecode(target_timecode)`
    *   **功能描述:** 将播放头移动到指定的时间码位置。
    *   **关键参数:** `target_timecode` (字符串)
    *   **返回值及其用途:** 在追加字幕片段到时间线之前，将播放头定位到正确的起始位置，确保字幕被放置在正确的时间点。

### `TimelineItem` 对象 (字幕片段)

*   **API 方法名:** `sub_obj.GetStart()`
    *   **功能描述:** 获取字幕片段在时间线上的起始帧号。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个整数，表示字幕开始显示的总帧数。用于计算起始时间码。
*   **API 方法名:** `sub_obj.GetEnd()`
    *   **功能描述:** 获取字幕片段在时间线上的结束帧号。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个整数，表示字幕结束显示的总帧数。用于计算结束时间码。
*   **API 方法名:** `sub_obj.GetName()`
    *   **功能描述:** 获取字幕片段的名称，对于字幕来说，这通常就是字幕的文本内容。
    *   **关键参数:** 无
    *   **返回值及其用途:** 返回一个字符串，即字幕的实际文本。

### `MediaPool` 对象

*   **API 方法名:** `media_pool.ImportMedia([srt_file_path])`
    *   **功能描述:** 将一个或多个媒体文件导入到媒体池中。
    *   **关键参数:** `[srt_file_path]` (列表)，包含要导入的文件的路径。
    *   **返回值及其用途:** 返回一个包含新创建的 `MediaPoolItem` 对象的列表。用于将 SRT 文件作为媒体资源导入 Resolve。
*   **API 方法名:** `media_pool.AppendToTimeline(subtitle_pool_item)`
    *   **功能描述:** 将媒体池中的一个项目追加到当前时间线的当前播放头位置。
    *   **关键参数:** `subtitle_pool_item` (`MediaPoolItem` 对象)
    *   **返回值及其用途:** 返回一个布尔值，指示操作是否成功。这是将导入的 SRT 字幕实际放置到新创建的字幕轨道上的关键步骤。

## 2. 模块功能总结

`ResolveIntegration` 类扮演着一个**适配器（Adapter）**和**外观（Facade）**的角色。它将 DaVinci Resolve 底层、有时较为复杂的 Scripting API 调用封装起来，为上层的应用程序逻辑（如 `services.py`）提供了一套更高级、更简洁、更安全的接口。

其核心功能总结如下：

1.  **初始化与连接管理:**
    *   在 `__init__` 和 `get_resolve` 方法中，它负责动态查找并连接到 DaVinci Resolve 的脚本环境。
    *   它优雅地处理了连接失败的情况，允许插件在没有 Resolve 环境的“离线模式”下运行，增强了程序的健壮性。

2.  **数据提取与格式化:**
    *   `get_subtitles_with_timecode` 是核心的数据提取方法。它不仅使用 `GetItemListInTrack` 获取原始字幕对象，还集成了 `TimecodeUtils` 工具类，将帧数（`GetStart`, `GetEnd`）转换为标准的时间码格式（`HH:MM:SS,ms`）。
    *   `export_subtitles_to_json` 和 `export_subtitles_to_srt` 方法基于提取的数据，将其格式化为通用的 JSON 和 SRT 格式，供插件 UI 显示或文件导出使用。

3.  **时间线操作封装:**
    *   `set_active_subtitle_track` 封装了轨道的启用/禁用逻辑，提供了一个简单的“设置活动轨道”功能。
    *   `reimport_from_json_file` 是最复杂的功能之一。它将一系列底层 API 调用（创建临时 SRT 文件、`ImportMedia`、`AddTrack`、`SetCurrentTimecode`、`AppendToTimeline`）组合成一个单一的、原子性的“重新导入字幕”操作，极大地简化了上层逻辑的实现。

4.  **错误处理:**
    *   几乎所有与 Resolve API 交互的方法都包裹在 `try...except` 块中。
    *   它将底层的、可能模糊的 API 异常转换为清晰、统一的错误信息（`(None, str)` 元组），方便上层调用者进行处理和向用户展示。

通过这种封装，`ResolveIntegration` 成功地将“如何与 DaVinci Resolve 交互”的复杂性与“应用程序需要什么功能”的业务逻辑分离开来，使得整个代码库更易于维护、测试和扩展。