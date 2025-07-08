# DaVinci Resolve SRT 导出与重导入工作流

## 核心流程

当前脚本的核心工作流程围绕着一个临时的 `subtitles.json` 文件，该文件作为UI界面和DaVinci Resolve之间的主要数据交换媒介。

1.  **导出到JSON**: 当用户在UI中选择一个字幕轨道时，脚本会将该轨道的字幕内容（文本和时间码）导出到 `subtitles.json` 文件。JSON中存储的时间码格式为标准的SRT格式 **`HH:MM:SS,ms`** (时:分:秒,毫秒)。
2.  **UI编辑**: 用户在界面上对字幕的所有修改都会被实时地保存在内存中，并同步更新到 `subtitles.json` 文件。
3.  **重导入到Resolve**: 当用户触发“重导入”功能时，脚本会执行一个“JSON -> SRT -> Resolve”的转换流程：
    a.  读取 `subtitles.json` 文件。
    b.  将JSON中的数据转换为标准的SRT格式字符串。
    c.  通过Resolve的API将生成的SRT内容导入到时间线的一个新轨道上。

## 时间码转换详解

从JSON到SRT的转换过程中，时间码的处理是一个关键步骤，确保了跨平台的时间精度。

### 步骤 1: 时间码字符串 -> 总帧数

-   **函数**: `timecode_to_frames(tc_str: str, frame_rate: float)`
-   **位置**: `src/resolve_integration.py`
-   **输入**: `HH:MM:SS,ms` 格式的时间码字符串（来自 `subtitles.json`）。
-   **处理**:
    1.  以逗号 `,` 分割秒和毫秒，再以冒号 `:` 分割时、分、秒。
    2.  将包括毫秒在内的总时间转换为秒: `总秒数 = (时 * 3600) + (分 * 60) + 秒 + (毫秒 / 1000.0)`
    3.  根据项目帧率 (`frame_rate`) 计算总帧数并四舍五入: `总帧数 = int(round(总秒数 * 帧率))`
-   **输出**: 一个代表绝对时间位置的整数（总帧数）。

### 步骤 2: 总帧数 -> SRT时间格式

-   **函数**: `TimecodeUtils.timecode_to_srt_format(frame, frame_rate)`
-   **位置**: `src/timecode_utils.py`
-   **输入**: 上一步计算出的总帧数。
-   **处理**:
    1.  `总秒数 = 总帧数 / 帧率`
    2.  将包含小数的总秒数分解为时、分、秒和毫秒。
-   **输出**: `HH:MM:SS,ms` 格式的SRT标准时间字符串。

### 流程总结

`JSON ("HH:MM:SS,ms")` --> `timecode_to_frames()` --> `总帧数` --> `timecode_to_srt_format()` --> `SRT ("HH:MM:SS,ms")`

这个两步转换过程确保了时间码的精确性，使得生成的SRT文件能够在遵循SRT标准的任何软件中正确显示和同步。