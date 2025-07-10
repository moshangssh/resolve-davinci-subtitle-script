import re
import json
import os
import tempfile

class SubtitleManager:
    """
    Manages subtitle data, including loading, processing, and saving.
    """
    def __init__(self, resolve_integration, data_model):
        self.resolve_integration = resolve_integration
        self.data_model = data_model
        self.subtitles_data = []
        self.raw_obj_map = {}
        self.current_json_path = None
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'subvigator_cache')
        self.current_track_index = None

    def load_subtitles(self, track_index):
        """
        Loads subtitles from the cache.
        """
        self.current_track_index = track_index
        file_path = os.path.join(self.cache_dir, f"track_{track_index}.json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.subtitles_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.subtitles_data = []
        
        return self.subtitles_data

    def get_subtitles(self):
        return self.subtitles_data

    def update_subtitle_text(self, item_id, new_text):
        """Updates the text of a single subtitle and saves the changes."""
        sub_obj = next((s for s in self.subtitles_data if s['index'] == item_id), None)
        if sub_obj:
            sub_obj['text'] = new_text
            self._save_changes_to_json()
            return True
        return False

    def handle_replace_current(self, item_id, find_text, replace_text):
        """Handles replacing the text of a single subtitle item."""
        if not find_text:
            return None
        sub_obj = next((s for s in self.subtitles_data if s['index'] == item_id), None)
        if sub_obj:
            original_text = sub_obj['text']
            new_text = original_text.replace(find_text, replace_text, 1)
            if original_text != new_text:
                sub_obj['text'] = new_text
                self._save_changes_to_json()
                return {'index': item_id, 'old': original_text, 'new': new_text}
        return None

    def handle_replace_all(self, find_text, replace_text):
        """Handles replacing text across all subtitle items."""
        if not find_text:
            return []
        
        changes = []
        for sub_obj in self.subtitles_data:
            original_text = sub_obj['text']
            new_text = original_text.replace(find_text, replace_text)
            if original_text != new_text:
                changes.append({'index': sub_obj['index'], 'old': original_text, 'new': new_text})
                sub_obj['text'] = new_text
        
        if changes:
            self._save_changes_to_json()
        
        return changes

    def _save_changes_to_json(self):
        """Saves the current subtitle data to the JSON file."""
        if self.current_track_index is None:
            print("Error: No current track index is set. Cannot save.")
            return

        file_path = os.path.join(self.cache_dir, f"track_{self.current_track_index}.json")
        
        try:
            output_data = []
            for sub in self.subtitles_data:
                clean_text = re.sub(r'<[^>]+>', '', sub.get('text', ''))
                output_data.append({
                    "index": sub.get('index'),
                    "start": sub.get('start'),
                    "end": sub.get('end'),
                    "text": clean_text,
                })

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            print(f"Failed to auto-save subtitle changes: {e}")