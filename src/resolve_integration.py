# resolve_integration.py
import json
import tempfile
import os
import sys
import platform
from src.timecode_utils import TimecodeUtils
from src.format_converter import convert_json_to_srt, format_subtitles_to_srt

class ResolveIntegration:
    def __init__(self):
        self.resolve = self.get_resolve()
        self.project_manager = None
        self.project = None
        self.timeline = None
        if self.resolve:
            print("LOG: INFO: DaVinci Resolve instance found. Initializing integration.")
            self.initialized = True
            self.project_manager = self.resolve.GetProjectManager()
            self.project = self.project_manager.GetCurrentProject()
            self.timeline = self.project.GetCurrentTimeline()
        else:
            self.initialized = False
            print("LOG: INFO: DaVinci Resolve instance not found. Running in offline mode.")

    def _get_resolve_bmd(self):
        """
        Dynamically adds the Resolve scripting path and returns the Resolve object.
        """
        if platform.system() == "Windows":
            script_module_path = os.getenv("PROGRAMDATA") + "\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules\\"
        elif platform.system() == "Darwin":
            script_module_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/"
        else: # Linux
            script_module_path = "/opt/resolve/libs/Fusion/Modules/"

        if not os.path.exists(script_module_path):
            print(f"LOG: ERROR: Resolve scripting module path not found: {script_module_path}")
            return None

        sys.path.append(script_module_path)
        try:
            import DaVinciResolveScript as bmd
            return bmd.scriptapp("Resolve")
        except ImportError:
            print("LOG: ERROR: Failed to import DaVinciResolveScript module.")
            return None

    def get_resolve(self):
        """
        Finds and returns the DaVinci Resolve script application instance.
        """
        # First, try the standard external connection method
        resolve_app = self._get_resolve_bmd()
        if resolve_app:
            return resolve_app

        # Fallback for internal/legacy environments
        try:
            import fusionscript
            print("LOG: INFO: Falling back to fusionscript.")
            return fusionscript.scriptapp("Resolve")
        except ImportError:
            return None

    def get_current_timeline_info(self):
        """
        Safely retrieves timeline information.

        Returns:
            tuple: (dict, None) on success, (None, str) on failure.
        """
        if not self.timeline:
            return None, "No active timeline."
        try:
            info = {
                'frame_rate': self.timeline.GetSetting('timelineFrameRate'),
                'track_count': self.timeline.GetTrackCount('subtitle'),
            }
            return info, None
        except Exception as e:
            return None, f"Failed to get timeline info: {e}"

    def get_subtitles(self, track_number=1):
        """
        Safely retrieves subtitles from a specific track.

        Returns:
            tuple: (list, None) on success, (None, str) on failure.
        """
        if not self.timeline:
            return None, "No active timeline."
        try:
            subtitles = self.timeline.GetItemListInTrack('subtitle', track_number)
            return subtitles, None
        except Exception as e:
            return None, f"Failed to get subtitles for track {track_number}: {e}"
    def get_subtitles_with_timecode(self, track_number=1):
        """
        Safely retrieves subtitles with their timecode information.

        Returns:
            tuple: (list, None) on success, (None, str) on failure.
        """
        if not self.timeline:
            return None, "No active timeline."

        try:
            frame_rate = self.timeline.GetSetting('timelineFrameRate')
            
            subtitles, err = self.get_subtitles(track_number)
            if err:
                return None, err
            
            if not subtitles:
                return [], None # Return empty list if no subtitles, not an error

            subtitle_list = []
            for i, sub_obj in enumerate(subtitles):
                in_frame = sub_obj.GetStart()
                out_frame = sub_obj.GetEnd()

                subtitle_list.append({
                    'id': i + 1,
                    'text': sub_obj.GetName(),
                    'in_frame': in_frame,
                    'out_frame': out_frame,
                    'in_timecode': TimecodeUtils.timecode_to_srt_format(in_frame, frame_rate),
                    'out_timecode': TimecodeUtils.timecode_to_srt_format(out_frame, frame_rate),
                    'raw_obj': sub_obj,
                })
            return subtitle_list, None
        except Exception as e:
            return None, f"Failed to get subtitles with timecode: {e}"

    def set_active_subtitle_track(self, track_index: int):
        """
        Safely sets the active subtitle track.

        Returns:
            tuple: (bool, None) on success, (None, str) on failure.
        """
        if not self.timeline:
            return None, "No active timeline."
        
        try:
            subtitle_track_count = self.timeline.GetTrackCount("subtitle")
            if track_index < 1 or track_index > subtitle_track_count:
                return False, f"Track index {track_index} is out of bounds."

            for i in range(1, subtitle_track_count + 1):
                self.timeline.SetTrackEnable("subtitle", i, i == track_index)
            
            return True, None
        except Exception as e:
            return None, f"Failed to set active subtitle track: {e}"
    def export_subtitles_to_json(self, track_number=1):
        subtitles, error = self.get_subtitles_with_timecode(track_number)
        if error:
            print(f"LOG: ERROR: Could not export subtitles to JSON due to: {error}")
            return None
        if not subtitles:
            return []

        output_data = []
        for sub in subtitles:
            output_data.append({
                "index": sub['id'],
                "start": sub['in_timecode'],
                "end": sub['out_timecode'],
                "text": sub['text']
            })
        return output_data

    def export_subtitles_to_srt(self, track_number=1, zero_based=False):
        if not self.timeline:
            return None

        subtitles_with_tc, error = self.get_subtitles_with_timecode(track_number)
        if error:
            print(f"LOG: ERROR: Could not export to SRT, failed to get subtitles: {error}")
            return None
        if not subtitles_with_tc:
            return ""

        frame_rate = float(self.timeline.GetSetting('timelineFrameRate'))
        timeline_start_timecode = self.timeline.GetStartTimecode()
        is_one_hour_start = timeline_start_timecode.startswith("01:")
        timeline_start_frame = self.timeline.GetStartFrame()

        # Determine the base frame to calculate relative timecodes
        base_frame = 0
        if zero_based:
            base_frame = timeline_start_frame
        elif is_one_hour_start:
            # If not zero-based and starts at 1 hour, the timecode is relative to the 1-hour mark
            base_frame = int(frame_rate * 3600)
        
        # The offset is only for the format converter, which expects an offset from a zero-based timeline.
        offset_frames = base_frame

        # Prepare subtitle list for the centralized converter
        subs_for_conversion = []
        for sub in subtitles_with_tc:
            subs_for_conversion.append({
                "start": sub['in_timecode'],
                "end": sub['out_timecode'],
                "text": sub['text']
            })

        # Generate SRT content using the centralized function
        srt_content = format_subtitles_to_srt(subs_for_conversion, frame_rate, offset_frames)
        return srt_content

    def reimport_from_json_file(self, json_path):
        """
        Re-imports subtitles from a JSON file onto a new, isolated
        subtitle track at the correct timecode.
        Returns:
            tuple: (bool, None) on success, (None, str) on failure.
        """
        if not self.timeline or not self.project:
            return None, "No active timeline or project."

        try:
            media_pool = self.project.GetMediaPool()
            if not media_pool:
                return None, "Could not get Media Pool."

            with open(json_path, 'r', encoding='utf-8') as f:
                subtitle_data = json.load(f)

            if not subtitle_data:
                return False, "No subtitles to import from JSON."

            frame_rate = float(self.timeline.GetSetting('timelineFrameRate'))
            timeline_start_frame = self.timeline.GetStartFrame()
            srt_content = convert_json_to_srt(json_path, frame_rate, offset_frames=timeline_start_frame)

            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.srt', encoding='utf-8') as tmp_srt_file:
                tmp_srt_file.write(srt_content)
                srt_file_path = tmp_srt_file.name

            try:
                imported_media = media_pool.ImportMedia([srt_file_path])
                if not imported_media:
                    return None, "Failed to import SRT file into Media Pool."
                subtitle_pool_item = imported_media[0]

                self.timeline.AddTrack("subtitle")
                new_track_count = self.timeline.GetTrackCount("subtitle")
                for i in range(1, new_track_count + 1):
                    self.timeline.SetTrackEnable("subtitle", i, i == new_track_count)
                
                first_subtitle_start_tc = subtitle_data[0]['start']
                first_subtitle_frame = TimecodeUtils.timecode_to_frames(first_subtitle_start_tc, frame_rate)
                target_timecode = TimecodeUtils.timecode_from_frame(first_subtitle_frame, frame_rate, self.timeline.GetSetting('timelineDropFrame') == '1')
                self.timeline.SetCurrentTimecode(target_timecode)

                if not media_pool.AppendToTimeline(subtitle_pool_item):
                    # Re-enable tracks even on failure for safety
                    for i in range(1, new_track_count + 1):
                        self.timeline.SetTrackEnable("subtitle", i, True)
                    return None, "Failed to append clip to the timeline."

                print("LOG: SUCCESS: Subtitles re-imported and placed correctly on a new, isolated track.")
                return True, None
            finally:
                if os.path.exists(srt_file_path):
                    os.remove(srt_file_path)

        except (IOError, json.JSONDecodeError) as e:
            return None, f"File or JSON processing error: {e}"
        except (KeyError, IndexError) as e:
            return None, f"Data structure error in JSON file: {e}"
        except Exception as e:
            return None, f"An unexpected exception occurred: {e}"


