# resolve_integration.py
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