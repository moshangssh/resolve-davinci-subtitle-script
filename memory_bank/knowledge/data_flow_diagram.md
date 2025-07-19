# 数据流图：刷新轨道字幕

本文档旨在通过序列图（Sequence Diagram）详细阐述用户在 Subvigator 应用中执行“刷新轨道字幕”操作时的完整端到端数据流。

## 参与者（Actors/Participants）

- **User**: 应用的最终用户。
- **SubvigatorWindow (ui.py)**: 用户界面层，负责接收用户输入和展示数据。
- **ApplicationController (main.py)**: 应用控制器，作为UI和后端服务之间的协调者。
- **AppService (services.py)**: 应用服务层，封装核心业务逻辑。
- **SubtitleManager (subtitle_manager.py)**: 字幕数据管理器，负责字幕的加载、缓存和处理。
- **ResolveIntegration (resolve_integration.py)**: 与 DaVinci Resolve API 交互的集成层。
- **DaVinci Resolve**: 外部视频编辑软件，是数据的最终来源。

## 序列图 (Mermaid)

```mermaid
sequenceDiagram
    participant User
    participant SubvigatorWindow (ui.py)
    participant ApplicationController (main.py)
    participant AppService (services.py)
    participant SubtitleManager (subtitle_manager.py)
    participant ResolveIntegration (resolve_integration.py)
    participant DaVinci Resolve

    User->>SubvigatorWindow (ui.py): 点击 "获取字幕" 按钮
    SubvigatorWindow (ui.py)->>ApplicationController (main.py): 触发 refresh_button.clicked 信号

    ApplicationController (main.py)->>AppService (services.py): 调用 on_refresh_button_clicked()
    AppService (services.py)->>ResolveIntegration (resolve_integration.py): 调用 refresh_timeline_info()
    ResolveIntegration (resolve_integration.py)->>DaVinci Resolve: 调用 timeline.GetTrackCount('subtitle')
    DaVinci Resolve-->>ResolveIntegration (resolve_integration.py): 返回轨道数量 (track_count)
    ResolveIntegration (resolve_integration.py)-->>AppService (services.py): 返回 timeline_info
    AppService (services.py)-->>ApplicationController (main.py): 返回 timeline_info

    ApplicationController (main.py)->>ApplicationController (main.py): 更新UI中的轨道下拉列表
    ApplicationController (main.py)->>AppService (services.py): 调用 on_track_changed() 触发默认轨道加载
    AppService (services.py)->>ResolveIntegration (resolve_integration.py): 调用 change_active_track(track_index)
    ResolveIntegration (resolve_integration.py)->>DaVinci Resolve: 调用 timeline.SetTrackEnable()
    DaVinci Resolve-->>ResolveIntegration (resolve_integration.py): 返回成功/失败
    ResolveIntegration (resolve_integration.py)-->>AppService (services.py): 返回成功/失败

    AppService (services.py)->>SubtitleManager (subtitle_manager.py): 调用 load_subtitles(track_index)
    
    SubtitleManager (subtitle_manager.py)->>SubtitleManager (subtitle_manager.py): 检查本地缓存 (track_{index}.json)
    alt 缓存未命中 (Cache Miss)
        SubtitleManager (subtitle_manager.py)->>ResolveIntegration (resolve_integration.py): 调用 export_subtitles_to_json(track_index)
        ResolveIntegration (resolve_integration.py)->>DaVinci Resolve: 调用 GetItemListInTrack()
        DaVinci Resolve-->>ResolveIntegration (resolve_integration.py): 返回原始字幕对象列表
        ResolveIntegration (resolve_integration.py)->>ResolveIntegration (resolve_integration.py): 格式化为JSON数据
        ResolveIntegration (resolve_integration.py)-->>SubtitleManager (subtitle_manager.py): 返回字幕JSON数据
        SubtitleManager (subtitle_manager.py)->>SubtitleManager (subtitle_manager.py): 将JSON数据写入缓存文件
    else 缓存命中 (Cache Hit)
        SubtitleManager (subtitle_manager.py)->>SubtitleManager (subtitle_manager.py): 从缓存文件读取JSON数据
    end

    SubtitleManager (subtitle_manager.py)-->>AppService (services.py): 返回字幕数据 (subtitles)
    AppService (services.py)-->>ApplicationController (main.py): 返回字幕数据 (subtitles)
    ApplicationController (main.py)->>SubvigatorWindow (ui.py): 调用 populate_table(subs_data=subtitles)
    SubvigatorWindow (ui.py)->>User: UI表格填充新数据，刷新完成

```

## 关键步骤解释

1.  **用户触发**: 流程始于用户在 `SubvigatorWindow` 中点击“获取字幕”按钮。
2.  **信号传递**: UI层通过信号 (`clicked`) 通知 `ApplicationController` 用户执行了操作。
3.  **服务调用**: `ApplicationController` 调用 `AppService` 中的 `refresh_timeline_info` 方法，开始获取时间线信息。
4.  **API交互**: `AppService` 将请求委托给 `ResolveIntegration`，后者直接调用 DaVinci Resolve 的 API (`GetTrackCount`) 来获取字幕轨道的数量。
5.  **轨道切换与加载**: 获取到轨道信息后，Controller 会触发默认轨道的加载流程。`AppService` 首先通过 `ResolveIntegration` 激活目标轨道，然后调用 `SubtitleManager` 的 `load_subtitles` 方法。
6.  **缓存检查 (核心)**: `SubtitleManager` 是数据加载的核心。它首先检查是否存在该轨道的本地JSON缓存。
    *   **缓存命中**: 如果存在，则直接从本地文件读取数据，避免了与 Resolve 的直接通信，提高了效率。
    *   **缓存未命中**: 如果不存在，`SubtitleManager` 会请求 `ResolveIntegration` 从 Resolve 中导出字幕 (`export_subtitles_to_json`)，然后将获取到的数据写入本地JSON文件作为缓存，以备后续使用。
7.  **数据返回**: `SubtitleManager` 将加载好的字幕数据层层返回给 `ApplicationController`。
8.  **UI更新**: `ApplicationController` 最终调用 `SubvigatorWindow` 的 `populate_table` 方法，将获取到的字幕数据填充到UI表格中，用户最终看到更新后的字幕列表。
