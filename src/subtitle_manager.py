import json

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

    def load_subtitles(self, track_index):
        """
        Loads subtitles from Resolve, stores them, and exports to a JSON file.
        """
        self.current_json_path = self.resolve_integration.export_subtitles_to_json(track_index)
        
        subs_data_with_raw = self.resolve_integration.get_subtitles_with_timecode(track_index)
        
        self.subtitles_data = []
        self.raw_obj_map = {}
        if subs_data_with_raw:
            for sub in subs_data_with_raw:
                self.raw_obj_map[sub['id']] = sub.pop('raw_obj', None)
                self.subtitles_data.append(sub)
        
        return self.subtitles_data

    def get_subtitles(self):
        return self.subtitles_data

    def update_subtitle_text(self, item_id, new_text):
        """Updates the text of a single subtitle and saves the changes."""
        sub_obj = next((s for s in self.subtitles_data if s['id'] == item_id), None)
        if sub_obj:
            sub_obj['text'] = new_text
            self._save_changes_to_json()
            return True
        return False

    def handle_replace_current(self, item_id, find_text, replace_text):
        """Handles replacing the text of a single subtitle item."""
        if not find_text:
            return None
        sub_obj = next((s for s in self.subtitles_data if s['id'] == item_id), None)
        if sub_obj:
            original_text = sub_obj['text']
            new_text = original_text.replace(find_text, replace_text, 1)
            if original_text != new_text:
                sub_obj['text'] = new_text
                self._save_changes_to_json()
                return {'id': item_id, 'old': original_text, 'new': new_text}
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
                changes.append({'id': sub_obj['id'], 'old': original_text, 'new': new_text})
                sub_obj['text'] = new_text
        
        if changes:
            self._save_changes_to_json()
        
        return changes

    def _save_changes_to_json(self):
        """Saves the current subtitle data to the JSON file."""
        if not self.current_json_path:
            print("Error: No current JSON file path is set. Cannot save.")
            return

        try:
            output_data = []
            for sub in self.subtitles_data:
                output_data.append({
                    "index": sub.get('id'),
                    "start": sub.get('in_timecode'),
                    "end": sub.get('out_timecode'),
                    "text": sub.get('text')
                })

            with open(self.current_json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            print(f"Failed to auto-save subtitle changes: {e}")