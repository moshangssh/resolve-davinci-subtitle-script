# SubtitleManager 技术分析文档

## 1. 概述

`SubtitleManager` 是字幕处理模块的核心，负责管理字幕数据的完整生命周期，包括数据的加载、处理、缓存和持久化。它的设计目标是提供一个高效、可靠的字幕数据管理层，将UI逻辑与底层的数据操作和Resolve API交互解耦。

该类的设计巧妙地运用了多种策略来优化性能和用户体验，主要包括：

*   **缓存机制 (Caching):** 避免与 DaVinci Resolve API 的频繁通信。
*   **延迟加载 (Lazy Loading):** 按需加载数据，加快应用启动和轨道切换速度。
*   **“脏”状态管理 (Dirty State Management):** 实现延迟写入，减少不必要的磁盘I/O操作。

## 2. 核心设计思想

### 2.1. 缓存机制

为了提升性能并减少对 DaVinci Resolve API 的依赖，`SubtitleManager` 实现了一套基于文件系统的缓存策略。

*   **缓存位置:** 缓存文件存储在系统的临时目录下的 `subvigator_cache` 文件夹中。每个字幕轨道的数据都会被保存为一个独立的JSON文件。

    ```python
    self.cache_dir = os.path.join(tempfile.gettempdir(), 'subvigator_cache')
    ```

*   **缓存文件命名:** 缓存文件根据其来源（轨道索引或导入文件）进行命名，例如 `track_1.json` 或 `imported_srt.json`。

    ```python
    file_path = os.path.join(self.cache_dir, f"track_{track_index}.json")
    self.current_json_path = file_path
    ```

*   **工作流程:**
    1.  当需要加载某个字幕轨道的数据时，系统首先会检查缓存目录中是否存在对应的JSON文件。
    2.  **缓存命中 (Cache Hit):** 如果文件存在，则直接从该文件加载字幕数据，避免了与Resolve的实时通信。
    3.  **缓存未命中 (Cache Miss):** 如果文件不存在，系统会通过 `resolve_integration.export_subtitles_to_json()` 从Resolve中导出该轨道的字幕，然后将其存入JSON文件作为缓存，供后续使用。

*   **优势:**
    *   **性能提升:** 直接从本地文件读取数据远快于通过API从Resolve中获取，极大地提升了数据加载速度。
    *   **离线能力:** 即便与Resolve的连接断开，用户依然可以查看和编辑已缓存的字幕数据。
    *   **降低API负载:** 减少了对Resolve API的调用次数，降低了潜在的性能瓶颈和出错风险。

### 2.2. 延迟加载 (Lazy Loading)

`SubtitleManager` 采用延迟加载策略，即只在用户明确请求访问某个字幕轨道时才加载相应的数据。

*   **实现方式:** 数据的加载操作由 `load_subtitles(track_index)` 方法触发。该方法只有在用户在UI上选择了一个新的字幕轨道时才会被 `AppService` 调用。

    ```python
    # 在 AppService 中
    def change_active_track(self, track_index):
        # ...
        subtitles = self.subtitle_manager.load_subtitles(track_index)
        return subtitles, None
    ```

*   **优势:**
    *   **快速启动:** 应用启动时无需加载任何字幕数据，加快了初始化速度。
    *   **资源节约:** 避免了一次性加载所有轨道的字幕数据，节约了内存和CPU资源，尤其是在处理包含大量字幕轨道的项目时效果显著。

### 2.3. “脏”状态管理 (`is_dirty` flag)

`is_dirty` 是一个布尔型标志位，用于追踪当前加载的字幕数据是否已被修改但尚未持久化。这是实现延迟写入（Dirty-Write）策略的关键。

*   **工作机制:**
    1.  当字幕数据被加载时，`is_dirty` 默认为 `False`。
    2.  当用户执行任何修改操作（如更新文本、替换、导入SRT）时，`is_dirty` 会被设置为 `True`。

        ```python
        def update_subtitle_text(self, item_id, new_text):
            # ...
            self.is_dirty = True
            # ...

        def load_subtitles_from_srt_content(self, srt_content: str):
            # ...
            self.is_dirty = True
            # ...
        ```
    3.  写回操作并不会在每次修改后立即执行，而是被推迟到以下关键时刻，由 `AppService` 统一协调触发：
        *   **切换轨道时:** 在加载新轨道前，保存当前“脏”轨道的修改。
        *   **执行“导出并重新导入”操作时:** 确保将最新的修改写回到Resolve。

        ```python
        # 在 AppService 中
        def change_active_track(self, track_index):
            if self.subtitle_manager.is_dirty:
                self.subtitle_manager._save_changes_to_json()
                self.subtitle_manager.is_dirty = False
            # ...

        def export_and_reimport_subtitles(self):
            if self.subtitle_manager.is_dirty:
                self.subtitle_manager._save_changes_to_json()
            # ...
        ```

*   **优势:**
    *   **性能优化:** 避免了在用户的每一次按键或微小改动后都执行耗时的文件写入操作，将多次写入合并为一次，显著降低了磁盘I/O开销。
    *   **数据一致性:** 确保在执行关键流程（如切换轨道、重新导入）前，所有未保存的修改都被持久化，防止数据丢失。

### 2.4. 数据源处理

`SubtitleManager` 通过 `current_track_index` 和 `current_json_path` 两个属性来清晰地区分和管理不同的数据来源。

*   **Resolve轨道数据:** 当从Resolve的某个轨道加载数据时，`current_track_index` 会被设置为相应的轨道号（大于0），`current_json_path` 则指向该轨道的缓存文件。
*   **导入的SRT文件数据:** 当用户通过UI导入一个SRT文件时，`current_track_index` 会被设置为一个特殊值 `0`，而 `current_json_path` 会指向一个固定的缓存文件 `imported_srt.json`。这使得系统能够明确区分当前操作的数据是源于Resolve还是外部文件。

    ```python
    def load_subtitles_from_srt_content(self, srt_content: str):
        # ...
        self.current_track_index = 0
        self.current_json_path = os.path.join(self.cache_dir, 'imported_srt.json')
        # ...
    ```

## 3. 核心方法分析

### `_save_changes_to_json()`

这是一个私有方法，是数据持久化的核心。它负责将内存中当前的字幕数据 (`self.subtitles_data`) 写回到对应的JSON缓存文件中。

*   **HTML清理:** 在保存之前，该方法会调用 `utils.clean_html()` 函数来清理字幕文本中的所有HTML标签。这是为了确保写入缓存和最终导入Resolve的数据是纯净的文本，避免潜在的格式问题。

    ```python
    def _save_changes_to_json(self):
        # ...
        for sub in self.subtitles_data:
            clean_text = clean_html(sub.get('text', ''))
            output_data.append({
                # ...
                "text": clean_text,
            })
        # ...
    ```

*   **数据结构:** 保存到JSON文件中的数据结构是固定的，只包含 `index`, `start`, `end`, `text` 四个核心字段，确保了数据格式的统一和简洁。

## 4. 总结

`SubtitleManager` 通过其精心设计的缓存、延迟加载和状态管理机制，为上层应用提供了一个高效、健壮的数据服务。它成功地将复杂的数据操作和API交互细节封装起来，使得 `AppService` 和UI层可以更专注于业务逻辑本身，而无需关心底层的实现细节。