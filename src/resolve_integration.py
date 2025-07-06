# resolve_integration.py
class ResolveIntegration:
    def __init__(self):
        self.resolve = self._get_resolve_instance()
        if not self.resolve:
            raise ImportError("Could not connect to DaVinci Resolve. Make sure the application is running.")
        
        self.project_manager = self.resolve.GetProjectManager()
        self.project = self.project_manager.GetCurrentProject()
        self.timeline = self.project.GetCurrentTimeline()

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
    def set_active_subtitle_track(self, track_index: int):
        if not self.timeline:
            return False
        
        subtitle_track_count = self.timeline.GetTrackCount("subtitle")
        if track_index < 1 or track_index > subtitle_track_count:
            return False

        for i in range(1, subtitle_track_count + 1):
            self.timeline.SetTrackEnable("subtitle", i, i == track_index)
        
        return True