# timecode_utils.py
import platform
import math
import cffi
import os
import glob

class TimecodeUtils:
    def __init__(self, resolve=None):
        self.resolve = resolve
        self.ffi = None
        self.libavutil = None
        if self.resolve:
            self.ffi = cffi.FFI()
            self._define_c_types()
            self.libavutil = self._load_library()

    def _define_c_types(self):
        self.ffi.cdef("""
            enum AVTimecodeFlag {
                AV_TIMECODE_FLAG_DROPFRAME      = 1<<0,
                AV_TIMECODE_FLAG_24HOURSMAX     = 1<<1,
                AV_TIMECODE_FLAG_ALLOWNEGATIVE  = 1<<2,
            };

            struct AVRational { int32_t num; int32_t den; };
            struct AVTimecode {
                int32_t start;
                enum AVTimecodeFlag flags;
                struct AVRational rate;
                uint32_t fps;
            };

            char* av_timecode_make_string(const struct AVTimecode* tc, const char* buf, int32_t framenum);
            int32_t av_timecode_init_from_string(struct AVTimecode* tc, struct AVRational rate, const char* str, void* log_ctx);
            const char* av_version_info(void);
        """)

    def _load_library(self):
        if not self.resolve:
            return None

        try:
            fu = self.resolve.Fusion()
        except AttributeError:
            raise ImportError("Could not get Fusion object from Resolve. Is Fusion running?")

        lib_name_pattern = ""
        if platform.system() == "Windows":
            lib_name_pattern = "avutil*.dll"
        elif platform.system() == "Darwin": # OSX
            lib_name_pattern = "libavutil*.dylib"
        else: # Linux
            lib_name_pattern = "libavutil.so"
            
        fusion_libs_path = fu.MapPath("FusionLibs:")
        
        # On non-Windows, the path might be one level up
        if platform.system() != "Windows":
             fusion_libs_path = os.path.abspath(os.path.join(fusion_libs_path, '..'))

        # Search for the library in the FusionLibs directory
        lib_path_search = os.path.join(fusion_libs_path, lib_name_pattern)
        found_libs = glob.glob(lib_path_search)

        if not found_libs:
            raise ImportError(f"Could not find library matching '{lib_name_pattern}' in '{fusion_libs_path}'")
        
        # Take the first match
        lib_path = found_libs[0]

        try:
            print(f"Attempting to load library from DaVinci Resolve's path: {lib_path}")
            return self.ffi.dlopen(lib_path)
        except OSError as e:
            error_message = (
                f"Failed to load '{lib_path}' from Resolve's internal directory.\n"
                f"Error: {e}\n"
                "This might indicate a problem with the Resolve installation or permissions."
            )
            raise ImportError(error_message)

    def get_frame_rates(self):
        return [16, 18, 23.976, 24, 25, 29.97, 30, 47.952, 48, 50, 59.94, 60, 72, 95.904, 96, 100, 119.88, 120]

    def get_fraction(self, frame_rate_string_or_number):
        frame_rate = float(str(frame_rate_string_or_number))
        for fr in self.get_frame_rates():
            if fr == frame_rate or math.floor(fr) == frame_rate:
                is_decimal = fr % 1 > 0
                denominator = 1001 if is_decimal else 100
                numerator = math.ceil(fr) * (1000 if is_decimal else denominator)
                return {'num': int(numerator), 'den': int(denominator)}
        raise ValueError(f"Invalid frame rate: {frame_rate_string_or_number}")

    def get_decimal(self, frame_rate_string_or_number):
        fraction = self.get_fraction(frame_rate_string_or_number)
        return float(f"{fraction['num'] / fraction['den']:.3f}")

    def frame_from_timecode(self, timecode, frame_rate):
        rate_frac = self.get_fraction(frame_rate)
        tc = self.ffi.new("struct AVTimecode *")
        rate = self.ffi.new("struct AVRational", rate_frac)
        timecode_bytes = timecode.encode('utf-8')
        
        result = self.libavutil.av_timecode_init_from_string(tc, rate, timecode_bytes, self.ffi.NULL)
        if result != 0:
            raise RuntimeError(f"avutil error code: {result}")
        return tc.start

    def timecode_from_frame(self, frame, frame_rate, drop_frame=False):
        # 1. 获取帧率的十进制表示
        decimal_fps = self.get_decimal(frame_rate)

        # 2. 构造 AVTimecode 结构体所需的 flags
        flags_value = 0
        if drop_frame:
            flags_value |= 1  # AV_TIMECODE_FLAG_DROPFRAME
        flags_value |= 2      # AV_TIMECODE_FLAG_24HOURSMAX

        # 3. 使用 cffi 创建 AVTimecode 结构体实例
        tc = self.ffi.new("struct AVTimecode *", {
            'start': 0,
            'flags': flags_value,
            'rate': {'num': 0, 'den': 0}, # 显式初始化
            'fps': math.ceil(decimal_fps)
        })

        # 4. 准备调用 av_timecode_make_string 所需的缓冲区
        buf = self.ffi.new("char[30]")

        # 5. 调用 C 函数
        result_ptr = self.libavutil.av_timecode_make_string(tc, buf, frame)

        # 6. 检查返回指针是否为空
        if result_ptr == self.ffi.NULL:
            return "00:00:00:00" # 或抛出异常

        # 7. 将返回的C字符串转换为Python字符串
        timecode_string = self.ffi.string(result_ptr).decode('utf-8')

        return timecode_string

    @staticmethod
    def timecode_to_srt_format(frame, frame_rate):
        if frame_rate == 0:
            return "00:00:00,000"
            
        total_seconds = frame / frame_rate
        
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds - int(total_seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    @staticmethod
    def timecode_to_frames(tc_str: str, frame_rate: float) -> int:
        """Converts HH:MM:SS,ms timecode string to total frames."""
        main_parts = tc_str.split(',')
        if len(main_parts) != 2:
            raise ValueError("Invalid timecode format. Expected HH:MM:SS,ms.")
            
        time_parts = main_parts[0].split(':')
        if len(time_parts) != 3:
            raise ValueError("Invalid timecode format. Expected HH:MM:SS,ms.")

        try:
            h, m, s = [int(p) for p in time_parts]
            ms = int(main_parts[1])
            
            # Convert total time to seconds, including milliseconds
            total_seconds = (h * 3600) + (m * 60) + s + (ms / 1000.0)
            # Calculate total frames and round to the nearest frame
            total_frames = int(round(total_seconds * frame_rate))
            return total_frames
        except ValueError:
            raise ValueError("Invalid timecode format. Components must be integers.")