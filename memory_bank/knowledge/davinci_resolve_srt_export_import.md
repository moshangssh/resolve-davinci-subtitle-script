# DaVinci Resolve 字幕导出与导入技术方案

## 1. 跨平台临时目录

- **库:** Python `tempfile`
- **方法:** `tempfile.TemporaryDirectory()`
- **描述:** 使用上下文管理器创建一个临时的、跨平台的目录，该目录在使用完毕后会自动清理。
- **示例:**
  ```python
  import tempfile
  import os

  with tempfile.TemporaryDirectory() as tmpdirname:
      subtitle_file_path = os.path.join(tmpdirname, "temp_subtitles.srt")
      # ... 执行导出和导入操作 ...
  ```

## 2. DaVinci Resolve 脚本 API

### A. 导出SRT字幕（手动实现）

DaVinci Resolve API 不支持直接导出 SRT 文件，需要手动实现。

- **核心步骤:**
  1. 获取当前时间线: `project.GetCurrentTimeline()`
  2. 遍历字幕轨道: `timeline.GetItemListInTrack("subtitle", trackIndex)`
  3. 对每个字幕项 `TimelineItem`，提取信息：
     - **开始/结束帧:** `item.GetStart()`, `item.GetEnd()`
     - **字幕文本:** `item.GetClipProperty()["Text"]` (需要验证属性键)
  4. 将帧数转换为SRT时间码格式 (`HH:MM:SS,ms`)。
  5. 按照SRT格式规范写入文件。

### B. 导入字幕文件到媒体池

- **方法:** `MediaPool.ImportMedia(filePath)`
- **描述:** 将文件导入到当前媒体池，返回一个 `MediaPoolItem` 列表。

### C. 创建新的字幕轨道

- **方法:** `Timeline.AddTrack("subtitle")`
- **描述:** 在时间线上添加一个新的字幕轨道。

### D. 添加媒体池项目到时间线

- **方法:** `MediaPool.AppendToTimeline(clipInfo)`
- **描述:** 将媒体池中的剪辑（`MediaPoolItem`）添加到指定的时间线轨道。
- **示例:**
  ```python
  clip_info = {
      "mediaPoolItem": subtitle_item,
      "trackIndex": track_index
  }
  media_pool.AppendToTimeline([clip_info])