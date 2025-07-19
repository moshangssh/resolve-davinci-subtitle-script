# 技术文档：`format_converter.py`

## 1. 模块核心职责

`format_converter.py` 模块是字幕格式转换的核心组件。它的主要职责是在两种数据表示形式之间进行双向转换：

1.  **SRT (SubRip Text) 格式字符串**: 一种广泛使用的、人类可读的字幕文件格式。
2.  **内部字幕数据结构**: 一个Python的字典列表 (`List[Dict]`)，其中每个字典代表一条字幕，包含 `index`, `start`, `end`, 和 `text` 等关键信息。

该模块确保了应用程序内部处理字幕数据与导入/导出标准SRT文件之间能够无缝衔接。

## 2. 公共函数分析

### 2.1 `format_subtitles_to_srt(subtitles: list, frame_rate: float, offset_frames: int = 0) -> str`

此函数负责将内部的字幕数据列表转换为一个完整的、符合SRT规范的字符串。

*   **功能**:
    1.  遍历输入的 `subtitles` 列表。
    2.  对于每一条字幕，它首先调用 `TimecodeUtils.timecode_to_frames()` 将 `start` 和 `end` 时间码字符串转换为总帧数。
    3.  应用 `offset_frames` 参数对帧数进行调整。这个偏移量通常用于将基于时间轴的绝对帧数转换为从0开始的相对帧数，这对于生成独立的SRT文件至关重要。例如，如果时间轴的起始时间码不是0，可以通过提供一个偏移量来校正所有字幕的时间。
    4.  确保调整后的帧数不会是负数。
    5.  调用 `TimecodeUtils.timecode_to_srt_format()` 将校正后的帧数转换回 `HH:MM:SS,ms` 格式的SRT时间戳。
    6.  最后，将字幕的索引、处理后的时间戳和文本内容格式化为标准的SRT块，并用换行符将所有块连接成一个单一的字符串。

*   **错误处理**: 如果列表中的某个字幕条目缺少必要的键（如 `start`, `end`, `text`）或格式不正确，它会打印一条错误消息并跳过该条目，以确保程序的健壮性。

### 2.2 `convert_json_to_srt(json_path: str, frame_rate: float, offset_frames: int = 0) -> str`

这是一个便捷的工具函数，用于将存储在JSON文件中的字幕数据直接转换为SRT字符串。

*   **功能**:
    1.  接收一个JSON文件的路径 `json_path`。
    2.  打开并读取该JSON文件，将其内容解析为一个字幕数据列表。
    3.  将解析出的列表、帧率和偏移量直接传递给 `format_subtitles_to_srt()` 函数来完成最终的转换。

*   **错误处理**: 如果文件未找到或JSON格式无效，它会捕获异常，打印错误信息，并返回一个空字符串。

### 2.3 `parse_srt_content(srt_content: str) -> list`

此函数执行与 `format_subtitles_to_srt` 相反的操作：它将一个完整的SRT格式字符串解析成内部使用的字幕数据列表。

*   **功能**:
    1.  首先，它将输入的SRT字符串按空行分割成多个独立的字幕块。
    2.  然后，遍历每一个块，并将其按换行符分割成单独的行。
    3.  从这些行中提取字幕的索引、时间线（包含开始和结束时间）以及文本内容。
    4.  它将提取出的信息组装成一个标准的字幕字典（包含 `index`, `start`, `end`, `text` 键）。
    5.  所有解析出的字典被添加到一个列表中并最终返回。

*   **错误处理**: 如果某个SRT块的格式不符合预期（例如，缺少行或时间线格式错误），它会打印错误并跳过该块，以避免整个解析过程失败。

## 3. 与 `timecode_utils.py` 的协作

`format_converter.py` 与 `timecode_utils.py` 模块紧密协作，以实现关注点分离（Separation of Concerns）：

*   **`format_converter.py`**: 专注于**数据格式的解析和构建**。它理解SRT的结构和内部数据字典的结构，但不关心时间码背后的复杂数学计算。
*   **`timecode_utils.py`**: 专注于**时间码的数学运算**。它提供了一系列静态方法，用于在不同的时间表示（如 `HH:MM:SS:FF`、总帧数、SRT时间格式 `HH:MM:SS,ms`）之间进行精确转换。

通过这种方式，`format_converter.py` 在需要处理时间码时，会委托 `timecode_utils.py` 来执行这些计算。具体来说：

-   在从数据列表生成SRT时，它使用 `TimecodeUtils.timecode_to_frames()` 和 `TimecodeUtils.timecode_to_srt_format()`。
-   在解析SRT字符串时，虽然此版本直接提取时间字符串，但在后续处理中（如在 `subtitle_manager` 中），这些字符串通常会被 `TimecodeUtils` 的方法转换成帧数进行处理。

这种设计使得代码更清晰、更易于维护。如果未来需要更改时间码的计算逻辑或支持新的时间格式，只需修改 `timecode_utils.py`，而无需触及 `format_converter.py` 的代码。