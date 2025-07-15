# timecode_utils.py
import platform
import math
import cffi
import os
import glob
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        elif platform.system() == "Darwin":
            lib_name_pattern = "libavutil*.dylib"
        else:
            lib_name_pattern = "libavutil.so"

        fusion_libs_path = fu.MapPath("FusionLibs:")

        if platform.system() != "Windows":
            fusion_libs_path = os.path.abspath(os.path.join(fusion_libs_path, '..'))

        lib_path_search = os.path.join(fusion_libs_path, lib_name_pattern)
        found_libs = glob.glob(lib_path_search)

        if not found_libs:
            raise ImportError(f"Could not find library matching '{lib_name_pattern}' in '{fusion_libs_path}'")

        lib_path = None
        if len(found_libs) > 1:
            logging.info(f"Found multiple libraries: {found_libs}. Attempting to select the latest version.")
            best_version = -1
            selected_lib = None
            
            for lib in found_libs:
                # Extract version number from filename, e.g., avutil-58.dll or libavutil.58.dylib
                match = re.search(r'(\d+)\.(dll|dylib|so)', os.path.basename(lib))
                if not match:
                    match = re.search(r'-(\d+)\.dll', os.path.basename(lib))

                if match:
                    version = int(match.group(1))
                    if version > best_version:
                        best_version = version
                        selected_lib = lib
                else:
                    logging.warning(f"Could not parse version from '{lib}'.")

            if selected_lib:
                lib_path = selected_lib
                logging.info(f"Selected library with highest version: {lib_path}")
            else:
                logging.warning("Could not determine the best library version. Falling back to the first one found.")
                lib_path = found_libs[0]
        else:
            lib_path = found_libs[0]

        try:
            logging.info(f"Attempting to load library from DaVinci Resolve's path: {lib_path}")
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
        try:
            frame_rate = float(str(frame_rate_string_or_number))
        except ValueError:
            raise ValueError(f'Invalid frame rate format: {frame_rate_string_or_number}')
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

    def frame_from_timecode(self, timecode, frame_rate, drop_frame=False):
        if self.libavutil:
            try:
                rate_frac = self.get_fraction(frame_rate)
                tc = self.ffi.new("struct AVTimecode *")
                rate = self.ffi.new("struct AVRational", rate_frac)
                timecode_bytes = timecode.encode('utf-8')
                
                result = self.libavutil.av_timecode_init_from_string(tc, rate, timecode_bytes, self.ffi.NULL)
                if result != 0:
                    raise RuntimeError(f"avutil error code: {result}")
                return tc.start
            except (RuntimeError, ValueError) as e:
                raise ValueError(f'Invalid timecode format: {timecode} - {e}')
        else:
            return self._python_timecode_to_frame(timecode, frame_rate, drop_frame)

    def timecode_from_frame(self, frame, frame_rate, drop_frame=False):
        if self.libavutil:
            frame = max(0, frame)
            decimal_fps = self.get_decimal(frame_rate)
            flags_value = 0
            if drop_frame:
                flags_value |= 1
            flags_value |= 2

            tc = self.ffi.new("struct AVTimecode *", {
                'start': 0,
                'flags': flags_value,
                'rate': {'num': 0, 'den': 0},
                'fps': math.ceil(decimal_fps)
            })

            buf = self.ffi.new("char[30]")
            result_ptr = self.libavutil.av_timecode_make_string(tc, buf, frame)

            if result_ptr == self.ffi.NULL:
                return "00:00:00:00"

            return self.ffi.string(result_ptr).decode('utf-8')
        else:
            return self._python_frame_to_timecode(frame, frame_rate, drop_frame)

    def _python_timecode_to_frame(self, timecode: str, frame_rate: float, drop_frame: bool) -> int:
        parts = timecode.replace(';', ':').split(':')
        if len(parts) != 4:
            raise ValueError("Timecode must be in HH:MM:SS:FF format.")

        try:
            h, m, s, f = [int(p) for p in parts]
        except ValueError:
            raise ValueError("Timecode components must be integers.")

        fps_int = int(round(frame_rate))
        total_frames = (h * 3600 + m * 60 + s) * fps_int + f

        if drop_frame:
            # Drop-frame calculation is complex. This is a simplified placeholder.
            # A full implementation would be needed for perfect accuracy.
            # For 29.97/59.94, 2 frames are dropped each minute, except every 10th minute.
            if fps_int in (30, 60): # Approximation for 29.97/59.94
                total_minutes = h * 60 + m
                num_drops = 2 * (total_minutes - total_minutes // 10)
                if fps_int == 60:
                    num_drops *= 2
                total_frames -= num_drops
                
        return total_frames

    def _python_frame_to_timecode(self, frame: int, frame_rate: float, drop_frame: bool) -> str:
        frame = max(0, int(frame))
        fps_decimal = self.get_decimal(frame_rate)
        fps_int = int(round(fps_decimal))

        if drop_frame and fps_int in (30, 60):
            # Simplified drop-frame logic
            frames_per_minute_nominal = fps_int * 60
            
            # Number of frames to drop per minute (e.g., 2 for 29.97)
            drop_frames = 2 if fps_int == 30 else 4

            # Number of 10-minute cycles
            d = frame // (frames_per_minute_nominal * 10 - drop_frames * 9)
            # Remainder of frames
            m = frame % (frames_per_minute_nominal * 10 - drop_frames * 9)

            if m > drop_frames:
                frame += drop_frames * 9 * d + drop_frames * ((m - drop_frames) // (frames_per_minute_nominal - drop_frames))
            else:
                frame += drop_frames * 9 * d

        total_seconds = frame / fps_decimal
        
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        seconds = int(total_seconds % 60)
        frames = frame % fps_int

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    @staticmethod
    def timecode_to_srt_format(frame, frame_rate):
        frame = max(0, frame)
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