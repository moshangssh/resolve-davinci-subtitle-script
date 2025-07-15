from .resolve_integration import ResolveIntegration
from .subtitle_manager import SubtitleManager


class AppService:
    def __init__(self, resolve_integration: ResolveIntegration, subtitle_manager: SubtitleManager):
        self.resolve_integration = resolve_integration
        self.subtitle_manager = subtitle_manager

    def export_and_reimport_subtitles(self):
        """
        Handles the core logic for exporting and re-importing subtitles.
        Returns a tuple (success, message).
        """
        if self.subtitle_manager.current_json_path is None:
            return False, "无法获取字幕文件路径，请先选择一个轨道。"

        print("LOG: INFO: Starting export and re-import process from service.")
        success, error = self.resolve_integration.reimport_from_json_file(
            self.subtitle_manager.current_json_path
        )
        if error:
            return False, f"导入/导出失败: {error}"
        
        self.subtitle_manager.is_dirty = False
        return True, "字幕已成功导入到新的轨道。"

    def change_active_track(self, track_index):
        """
        Handles the logic for changing the active subtitle track.
        Returns a tuple (subtitles, error_message).
        """
        success, error = self.resolve_integration.set_active_subtitle_track(track_index)
        if error:
            return None, f"切换轨道失败: {error}"
        
        subtitles = self.subtitle_manager.load_subtitles(track_index)
        return subtitles, None

    def refresh_timeline_info(self):
        """
        Refreshes timeline information from Resolve.
        Returns a tuple (timeline_info, error_message).
        """
        timeline_info, error = self.resolve_integration.get_current_timeline_info()
        if error:
            return None, f"刷新失败: {error}"
        if not timeline_info:
            return None, "未能获取时间线信息，请确保DaVinci Resolve中已打开项目和时间线。"
        return timeline_info, None

    def replace_current_subtitle(self, item_index, find_text, replace_text):
        """
        Handles replacing the text of a single subtitle item.
        Returns the change dictionary if successful, otherwise None.
        """
        change = self.subtitle_manager.handle_replace_current(item_index, find_text, replace_text)
        if change:
            self.subtitle_manager.update_subtitle_text(change['index'], change['new'])
        return change

    def replace_all_subtitles(self, find_text, replace_text):
        """
        Handles replacing text across all subtitle items.
        Returns a list of changes.
        """
        changes = self.subtitle_manager.handle_replace_all(find_text, replace_text)
        if changes:
            self.subtitle_manager._save_changes_to_json()
        return changes