# resolve_integration.py
import json
import tempfile
import os
from .timecode_utils import TimecodeUtils
class ResolveIntegration:
    def __init__(self):
        self.resolve = self._get_resolve_instance()
        if not self.resolve:
            raise ImportError("Could not connect to DaVinci Resolve. Make sure the application is running.")
        
        self.project_manager = self.resolve.GetProjectManager()
        self.project = self.project_manager.GetCurrentProject()
        self.timeline = self.project.GetCurrentTimeline()
        try:
            self.tc_utils = TimecodeUtils(self.resolve)
        except Exception as e:
            print(f"Error initializing TimecodeUtils: {e}")
            self.tc_utils = None

    def _get_resolve_instance(self):
        try:
            import fusionscript
            return fusionscript.scriptapp("Resolve")
        except ImportError:
            pass # Try the next import
        try:
            import DaVinciResolveScript as dvr_script
            return dvr_script.scriptapp("Resolve")
        except ImportError:
            return None

    def get_current_timeline_info(self):
        if not self.timeline:
            return None
        return {
            'frame_rate': self.timeline.GetSetting('timelineFrameRate'),
            'track_count': self.timeline.GetTrackCount('subtitle'),
        }

    def get_subtitles(self, track_number=1):
        if not self.timeline:
            return []
        return self.timeline.GetItemListInTrack('subtitle', track_number)
    def get_subtitles_with_timecode(self, track_number=1):
        if not self.timeline:
            return []

        frame_rate = self.timeline.GetSetting('timelineFrameRate')
        drop_frame = self.timeline.GetSetting('timelineDropFrame') == '1'

        subtitles = self.get_subtitles(track_number)
        if not subtitles:
            return []

        if not self.tc_utils:
            print("TimecodeUtils not available.")
            return []

        subtitle_list = []
        for i, sub_obj in enumerate(subtitles):
            in_frame = sub_obj.GetStart()
            out_frame = sub_obj.GetEnd()

            subtitle_list.append({
                'id': i + 1,
                'text': sub_obj.GetName(),
                'in_frame': in_frame,
                'out_frame': out_frame,
                'in_timecode': self.tc_utils.timecode_from_frame(in_frame, frame_rate, drop_frame),
                'out_timecode': self.tc_utils.timecode_from_frame(out_frame, frame_rate, drop_frame),
                'raw_obj': sub_obj,
            })
        return subtitle_list

    def set_active_subtitle_track(self, track_index: int):
        if not self.timeline:
            return False
        
        subtitle_track_count = self.timeline.GetTrackCount("subtitle")
        if track_index < 1 or track_index > subtitle_track_count:
            return False

        for i in range(1, subtitle_track_count + 1):
            self.timeline.SetTrackEnable("subtitle", i, i == track_index)
        
        return True
    def export_subtitles_to_json(self, track_number=1):
        subtitles = self.get_subtitles_with_timecode(track_number)
        if not subtitles:
            return None


        output_data = []
        for sub in subtitles:
            output_data.append({
                "index": sub['id'],
                "start": sub['in_timecode'],
                "end": sub['out_timecode'],
                "text": sub['text']
            })

        try:
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, "subtitles.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            return file_path
        except Exception as e:
            print(f"Error exporting subtitles to JSON: {e}")
            return None
            
    def export_subtitles_to_srt(self, track_number=1, zero_based=False):
        if not self.timeline:
            return None

        subtitles = self.get_subtitles_with_timecode(track_number)
        if not subtitles:
            return ""

        frame_rate = float(self.timeline.GetSetting('timelineFrameRate'))
        timeline_start_timecode = self.timeline.GetStartTimecode()
        
        # 检查时间线是否从01:00:00:00开始，并计算偏移量
        offset_frames = 0
        is_one_hour_start = timeline_start_timecode.startswith("01:")
        timeline_start_frame = self.timeline.GetStartFrame()
        
        # 如果是基于0的导出，起始帧就是时间线的绝对起始帧
        # 如果不是基于0的导出，并且时间线不是从1小时开始，那么我们认为它是从0开始的
        base_frame = timeline_start_frame if zero_based else 0
        
        # 如果不是基于0的导出，并且时间线是从1小时开始的，那么基准帧就是1小时的帧数
        if not zero_based and is_one_hour_start:
            base_frame = int(frame_rate * 3600)


        srt_content = ""
        for i, sub in enumerate(subtitles):
            # 从绝对帧号中减去基准帧号，得到相对帧号
            start_frame = sub['in_frame'] - (0 if zero_based and is_one_hour_start else base_frame)
            end_frame = sub['out_frame'] - (0 if zero_based and is_one_hour_start else base_frame)

            # 如果是基于0的导出，但时间线是从1小时开始的，需要额外减去1小时的偏移
            if zero_based and is_one_hour_start:
                offset_frames = int(frame_rate * 3600)
                start_frame -= offset_frames
                end_frame -= offset_frames


            start_time = self.tc_utils.timecode_to_srt_format(start_frame, frame_rate)
            end_time = self.tc_utils.timecode_to_srt_format(end_frame, frame_rate)
            
            srt_content += f"{i + 1}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{sub['text']}\n\n"

        return srt_content

    def export_and_reimport_subtitles(self, track_number=1):
        """
        Exports a zero-based SRT, and re-imports it onto a new, isolated
        subtitle track at the correct timecode.
        """
        if not self.timeline or not self.project or not self.tc_utils:
            print("ERROR: No active timeline, project, or timecode utility.")
            return False

        media_pool = self.project.GetMediaPool()
        if not media_pool:
            print("ERROR: Could not get Media Pool.")
            return False

        try:
            with tempfile.TemporaryDirectory() as tmpdirname:
                # 1. Get original subtitle data for positioning and export a zero-based SRT
                original_subtitles = self.get_subtitles_with_timecode(track_number)
                if not original_subtitles:
                    print("INFO: No subtitles to export.")
                    return False
                
                srt_content = self.export_subtitles_to_srt(track_number, zero_based=True)
                srt_file_path = os.path.join(tmpdirname, "temp_subtitles.srt")
                with open(srt_file_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)

                # 2. Import the zero-based SRT into the Media Pool
                imported_media = media_pool.ImportMedia([srt_file_path])
                if not imported_media:
                    print("ERROR: Failed to import SRT file.")
                    return False
                subtitle_pool_item = imported_media[0]

                # 3. Create a new track and isolate it by disabling all others
                self.timeline.AddTrack("subtitle")
                new_track_count = self.timeline.GetTrackCount("subtitle")
                for i in range(1, new_track_count + 1):
                    self.timeline.SetTrackEnable("subtitle", i, i == new_track_count)
                print(f"INFO: New track created at index {new_track_count} and isolated.")

                # 4. Set playhead to the original start position
                first_subtitle_frame = original_subtitles[0]['in_frame']
                target_timecode = self.tc_utils.timecode_from_frame(first_subtitle_frame, float(self.timeline.GetSetting('timelineFrameRate')), self.timeline.GetSetting('timelineDropFrame') == '1')
                self.timeline.SetCurrentTimecode(target_timecode)
                print(f"INFO: Playhead moved to original start time: {target_timecode}.")

                # 5. Append the clip to the isolated track at the playhead
                if not media_pool.AppendToTimeline(subtitle_pool_item):
                    print("ERROR: Failed to append clip to the timeline.")
                    # Re-enable tracks even on failure
                    for i in range(1, new_track_count + 1):
                        self.timeline.SetTrackEnable("subtitle", i, True)
                    return False
                
                # 6. Re-enable all subtitle tracks
                for i in range(1, new_track_count + 1):
                    self.timeline.SetTrackEnable("subtitle", i, True)

                print("SUCCESS: Subtitles re-imported and placed correctly.")
                return True

        except Exception as e:
            print(f"FATAL: An unexpected exception occurred: {e}")
            return False