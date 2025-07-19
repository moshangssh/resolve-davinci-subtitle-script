# `timecode_utils.py` API 使用文档

## 1. 简介

本文档详细介绍了 `src/timecode_utils.py` 模块的 API 和实现。`TimecodeUtils` 类是一个纯静态工具集，旨在提供一个健壮、高精度的服务，用于在**时间码字符串**、**总帧数**和 **SRT 时间格式**之间进行相互转换。

该模块的核心依赖是 `timecode` 这个第三方库，它极大地简化了时间码的计算和处理，避免了手动实现复杂的帧率和 Drop-Frame 逻辑。

## 2. 设计理念

-   **纯静态方法**: `TimecodeUtils` 中的所有方法都是 `@staticmethod`。这意味着你不需要创建类的实例即可调用它们，例如 `TimecodeUtils.timecode_to_frames(...)`。
-   **单一职责**: 该模块只专注于时间码和帧数之间的转换，不处理任何与 DaVinci Resolve API 或文件 I/O 相关的功能。
-   **依赖 `timecode` 库**: 所有核心的时间码解析和计算都委托给 `timecode` 库，确保了计算的准确性和对各种帧率（包括 Drop-Frame）的健robust支持。

## 3. API 详解

### 3.1. `TimecodeUtils.frame_from_timecode(timecode_str, frame_rate)`

-   **功能**: 将标准时间码字符串 (如 `"01:23:45:12"` 或 `"00:01:00;02"`) 转换为总帧数。
-   **参数**:
    -   `timecode_str (str)`: 要转换的时间码字符串。Drop-Frame 格式 (`;` 分隔符) 会被自动识别。
    -   `frame_rate (float)`: 视频的帧率。
-   **返回值**: `(int)` 对应的总帧数。
-   **示例**:
    ```python
    from src.timecode_utils import TimecodeUtils
    
    frames = TimecodeUtils.frame_from_timecode("00:00:01:00", 24)
    # -> 24
    ```

### 3.2. `TimecodeUtils.timecode_from_frame(frame, frame_rate, drop_frame)`

-   **功能**: 将总帧数转换为标准时间码字符串。
-   **参数**:
    -   `frame (int)`: 要转换的总帧数。
    -   `frame_rate (float)`: 视频的帧率。
    -   `drop_frame (bool)`: 是否使用 Drop-Frame 格式。`True` 会生成用 `;` 分隔的时间码。
-   **返回值**: `(str)` 格式化后的时间码字符串。
-   **示例**:
    ```python
    tc_str = TimecodeUtils.timecode_from_frame(1798, 29.97, drop_frame=True)
    # -> "00:01:00;02"
    ```

### 3.3. `TimecodeUtils.timecode_to_srt_format(frame, frame_rate)`

-   **功能**: 将总帧数转换为 SRT 字幕格式的时间戳 (`HH:MM:SS,ms`)。
-   **参数**:
    -   `frame (int)`: 要转换的总帧数。
    -   `frame_rate (float)`: 视频的帧率。
-   **返回值**: `(str)` SRT 格式的时间字符串。
-   **实现细节**: 此函数通过将总帧数除以帧率得到总秒数，然后将秒数格式化为 SRT 标准。
-   **示例**:
    ```python
    srt_time = TimecodeUtils.timecode_to_srt_format(24, 24)
    # -> "00:00:01,000"
    ```

### 3.4. `TimecodeUtils.timecode_to_frames(srt_time, frame_rate)`

-   **功能**: 将 SRT 字幕格式的时间戳 (`HH:MM:SS,ms`) 转换为总帧数。
-   **参数**:
    -   `srt_time (str)`: SRT 格式的时间字符串。
    -   `frame_rate (float)`: 视频的帧率。
-   **返回值**: `(int)` 对应的总帧数。
-   **实现细节**: 此函数首先将 SRT 时间字符串解析为总秒数，然后乘以帧率得到总帧数。
-   **示例**:
    ```python
    frames = TimecodeUtils.timecode_to_frames("00:00:01,000", 24)
    # -> 24
    ```

## 4. 模块功能总结

`TimecodeUtils` 通过封装 `timecode` 库，提供了一个简洁、可靠且易于使用的静态工具类。它将复杂的时间码逻辑抽象出来，使得上层应用（如 `resolve_integration.py` 和 `format_converter.py`）可以方便地进行时间码和帧数之间的转换，而无需关心底层的实现细节。这种设计提高了代码的可维护性和可读性。