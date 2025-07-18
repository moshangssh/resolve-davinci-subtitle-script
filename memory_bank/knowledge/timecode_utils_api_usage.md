# `timecode_utils.py` CFFI/FFmpeg API 调用分析报告

## 1. 简介

本文档详细分析了 `src/timecode_utils.py` 文件中通过 CFFI 调用 FFmpeg `avutil` 库的技术实现。`TimecodeUtils` 类旨在提供一个健壮、高精度的时间码与帧数互转服务，其核心策略是优先使用高性能的 `avutil` 库，并提供纯 Python 的后备方案。

## 2. CFFI 交互分析

### 2.1. C 定义 (`ffi.cdef`)

在 `_define_c_types` 方法中，通过 `self.ffi.cdef` 定义了与 FFmpeg `avutil` 库交互所需的 C 结构体和函数签名。

-   **声明的 C 函数签名**:
    -   `char* av_timecode_make_string(const struct AVTimecode* tc, const char* buf, int32_t framenum);`
    -   `int32_t av_timecode_init_from_string(struct AVTimecode* tc, struct AVRational rate, const char* str, void* log_ctx);`
    -   `const char* av_version_info(void);`

-   **声明的 C 结构体和枚举**:
    -   `struct AVRational`
    -   `struct AVTimecode`
    -   `enum AVTimecodeFlag`

### 2.2. 动态库加载 (`_load_library`)

该方法负责定位并加载 `avutil` 动态链接库。

-   **平台兼容性**: 根据操作系统动态生成库文件名模式（`avutil*.dll`, `libavutil*.dylib`, `libavutil.so`）。
-   **路径查找**: 使用 DaVinci Resolve 的 `Fusion().MapPath("FusionLibs:")` API 获取 Fusion 库的根目录进行搜索。
-   **版本选择**: 如果找到多个版本的库，会通过正则表达式解析文件名中的版本号，并选择最新版本，增强了健壮性。
-   **加载**: 使用 `self.ffi.dlopen(lib_path)` 将选定的库加载到内存中。
-   **错误处理**: 如果库未找到或加载失败，会抛出 `ImportError` 并提供详细信息。

## 3. `avutil` 函数调用详解

### 3.1. `lib.av_timecode_init_from_string`

-   **调用位置**: `frame_from_timecode` 方法。
-   **API 方法名**: `av_timecode_init_from_string`
-   **功能描述**: 将字符串格式的时间码（如 "01:23:45:12"）解析为 `AVTimecode` 结构体，并计算出总帧数。
-   **关键参数**:
    -   `tc`: 指向 `AVTimecode` 结构体的指针，用于存储解析结果。
    -   `rate`: `AVRational` 结构体，表示帧率的分数形式。
    -   `str`: UTF-8 编码的时间码字符串。
    -   `log_ctx`: 日志上下文，此处为 `NULL`。
-   **返回值及其用途**: 返回 `int32_t` 错误码。`0` 表示成功。插件通过检查此值来确认操作是否成功，并从 `tc.start` 字段获取总帧数。

### 3.2. `lib.av_timecode_make_string`

-   **调用位置**: `timecode_from_frame` 方法。
-   **API 方法名**: `av_timecode_make_string`
-   **功能描述**: 将总帧数转换为标准格式的时间码字符串（"HH:MM:SS:FF"）。
-   **关键参数**:
    -   `tc`: 指向 `AVTimecode` 结构体的指针，包含帧率和标志位信息。
    -   `buf`: 字符缓冲区，用于存储生成的时间码字符串。
    -   `framenum`: 要转换的总帧数。
-   **返回值及其用途**: 返回指向 `buf` 中时间码字符串的指针。若出错则返回 `NULL`。插件使用 `self.ffi.string()` 将 C 字符串转换为 Python 字符串。

## 4. 后备方案 (Fallback) 分析

当 `avutil` 库加载失败时，`TimecodeUtils` 会优雅地降级，使用纯 Python 方法进行转换。

-   **触发条件**: `self.libavutil` 为 `None`。
-   **后备实现**:
    -   `_python_timecode_to_frame`: 替代 `av_timecode_init_from_string`，通过字符串处理和数学运算将时间码转为帧数。包含简化的 Drop-Frame 计算。
    -   `_python_frame_to_timecode`: 替代 `av_timecode_make_string`，将帧数转为时间码字符串。同样包含简化的 Drop-Frame 计算。
-   **CFFI vs. Python 后备方案对比**:
    -   **功能**: CFFI 实现精确支持包括 Drop-Frame 在内的所有时间码标准，而 Python 后备方案中的 Drop-Frame 计算是近似实现，精度较低。
    -   **性能**: CFFI 调用预编译的 C 代码，性能远高于纯 Python 实现，尤其适合批量处理场景。

## 5. 模块功能总结

`TimecodeUtils` 类通过“CFFI 优先，Python 后备”的策略，提供了一个健壮、高精度且高性能的时间码/帧数互转服务。它能够智能地加载 Resolve 内置的 `avutil` 库以实现精确计算，并在库不可用时自动切换到纯 Python 实现，保证了插件的核心功能在任何环境下都可用。这种设计在性能、精度和健壮性之间取得了出色的平衡。