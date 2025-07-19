# `timecode` 库 API 研究

## 核心发现

### 1. 创建 `Timecode` 对象

可以从时间码字符串和帧率创建 `Timecode` 对象。

```python
from timecode import Timecode

tc_string = "01:23:45:12"
framerate = 29.97
tc = Timecode(framerate, tc_string)
# -> Timecode('29.97', '01:23:45;12')
```

也可以从总帧数和帧率创建。

```python
frames_count = 12345
framerate = 29.97
tc = Timecode(framerate, frames=frames_count)
# -> Timecode('29.97', '00:06:51;26')
```

### 2. 获取总帧数

`Timecode` 对象有一个 `frames` 属性，可以直接获取总帧数。

```python
total_frames = tc.frames
# -> 150613
```

### 3. 转换为 SRT 时间码格式

`timecode` 库本身不直接提供 SRT 格式的转换方法，但可以通过总帧数和帧率计算得出。

```python
# A common way is to calculate total seconds from total frames and framerate.
total_seconds_float = tc.frames / float(tc.framerate)
hours, remainder = divmod(total_seconds_float, 3600)
minutes, seconds_float = divmod(remainder, 60)
seconds = int(seconds_float)
milliseconds = int((seconds_float - seconds) * 1000)

srt_timecode = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"
# -> '01:23:45,458'

```

## 测试代码

完整的测试代码如下：

```python
# -*- coding: utf-8 -*-
"""
A temporary test file to explore the 'timecode' library API.
"""
from timecode import Timecode

# 1. How to create a Timecode object from a timecode string and a framerate
tc_string = "01:23:45:12"
framerate = 29.97
tc1 = Timecode(framerate, tc_string)

print(f"Created Timecode object from string '{tc_string}' at {framerate}fps: {tc1}")

# 2. How to get the total number of frames from a Timecode object
total_frames = tc1.frames
print(f"Total frames for {tc1}: {total_frames}")

# 3. How to create a Timecode object from a number of frames and a framerate
frames_count = 12345
tc2 = Timecode(framerate, frames=frames_count)
print(f"Created Timecode object from {frames_count} frames at {framerate}fps: {tc2}")

# 4. How to convert a Timecode object back to different string formats
# Default string representation
print(f"Default string for {tc1}: {str(tc1)}")

# SRT format with milliseconds
# The library doesn't have a direct .to_srt() method, but we can format it.
# A common way is to calculate total seconds from total frames and framerate.
total_seconds_float = tc1.frames / float(tc1.framerate)
hours, remainder = divmod(total_seconds_float, 3600)
minutes, seconds_float = divmod(remainder, 60)
seconds = int(seconds_float)
milliseconds = int((seconds_float - seconds) * 1000)

srt_timecode = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"
print(f"SRT format for {tc1}: {srt_timecode}")
