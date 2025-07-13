import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
import os
from src.subtitle_manager import SubtitleManager

@pytest.fixture
def mock_dependencies():
    """Pytest fixture to create mock objects for dependencies."""
    resolve_integration = MagicMock()
    return resolve_integration

@pytest.fixture
def subtitle_manager(mock_dependencies):
    """Pytest fixture to create a SubtitleManager instance with mocked dependencies."""
    resolve_integration = mock_dependencies
    return SubtitleManager(resolve_integration)

class TestSubtitleManager:

    def test_load_subtitles(self, subtitle_manager, mock_dependencies):
        """Test loading subtitles from Resolve."""
        resolve_integration = mock_dependencies
        track_index = 1
        json_path = "/fake/path/subtitles.json"
        mock_subs = [
            {'index': 1, 'start': '00:00:01:00', 'end': '00:00:03:00', 'text': 'Hello'},
            {'index': 2, 'start': '00:00:04:00', 'end': '00:00:06:00', 'text': 'World'}
        ]
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_subs))):
            loaded_data = subtitle_manager.load_subtitles(track_index)
        
        assert subtitle_manager.current_json_path == os.path.join(subtitle_manager.cache_dir, f"track_{track_index}.json")
        assert len(loaded_data) == 2
        assert loaded_data[0]['text'] == 'Hello'
        assert 'index' in loaded_data[0]

    def test_update_subtitle_text(self, subtitle_manager):
        """Test updating the text of a single subtitle."""
        subtitle_manager.subtitles_data = [
            {'index': 1, 'text': 'Old text'}
        ]
        with patch.object(subtitle_manager, '_save_changes_to_json') as mock_save:
            result = subtitle_manager.update_subtitle_text(1, 'New text')
            
            assert result is True
            assert subtitle_manager.subtitles_data[0]['text'] == 'New text'
            mock_save.assert_called_once()

    def test_update_subtitle_text_not_found(self, subtitle_manager):
        """Test updating text for a subtitle that doesn't exist."""
        subtitle_manager.subtitles_data = []
        with patch.object(subtitle_manager, '_save_changes_to_json') as mock_save:
            result = subtitle_manager.update_subtitle_text(99, 'New text')
            
            assert result is False
            mock_save.assert_not_called()

    def test_handle_replace_current(self, subtitle_manager):
        """Test replacing text in a single subtitle item."""
        subtitle_manager.subtitles_data = [
            {'index': 1, 'text': 'This is a test.'}
        ]
        with patch.object(subtitle_manager, '_save_changes_to_json') as mock_save:
            changes = subtitle_manager.handle_replace_current(1, 'test', 'great test')
            
            assert subtitle_manager.subtitles_data[0]['text'] == 'This is a great test.'
            assert changes == {'index': 1, 'old': 'This is a test.', 'new': 'This is a great test.'}
            mock_save.assert_called_once()

    def test_handle_replace_all(self, subtitle_manager):
        """Test replacing text across all subtitles."""
        subtitle_manager.subtitles_data = [
            {'index': 1, 'text': 'Test one, test two.'},
            {'index': 2, 'text': 'Another test.'},
            {'index': 3, 'text': 'No changes here.'}
        ]
        with patch.object(subtitle_manager, '_save_changes_to_json') as mock_save:
            changes = subtitle_manager.handle_replace_all('test', 'check')
            
            assert len(changes) == 2
            assert subtitle_manager.subtitles_data[0]['text'] == 'Test one, check two.' # Note: str.replace replaces all occurrences
            assert subtitle_manager.subtitles_data[1]['text'] == 'Another check.'
            assert subtitle_manager.subtitles_data[2]['text'] == 'No changes here.'
            assert subtitle_manager.is_dirty is True

    def test_save_changes_to_json(self, subtitle_manager):
        """Test saving subtitle changes to a JSON file."""
        subtitle_manager.current_track_index = 1
        subtitle_manager.subtitles_data = [
            {'index': 1, 'start': '00:01', 'end': '00:02', 'text': 'Line 1'},
            {'index': 2, 'start': '00:03', 'end': '00:04', 'text': 'Line 2'}
        ]
        
        m_open = mock_open()
        with patch('builtins.open', m_open):
            with patch('json.dump') as mock_json_dump:
                subtitle_manager._save_changes_to_json()

                expected_path = os.path.join(subtitle_manager.cache_dir, 'track_1.json')
                m_open.assert_called_once_with(expected_path, 'w', encoding='utf-8')
                
                expected_data = [
                    {"index": 1, "start": "00:01", "end": "00:02", "text": "Line 1"},
                    {"index": 2, "start": "00:03", "end": "00:04", "text": "Line 2"}
                ]
                mock_json_dump.assert_called_once_with(expected_data, m_open(), ensure_ascii=False, indent=2)

    def test_save_changes_to_json_no_path(self, subtitle_manager, capsys):
        """Test saving changes when no JSON path is set."""
        subtitle_manager.current_track_index = None
        subtitle_manager._save_changes_to_json()
        captured = capsys.readouterr()
        assert "Error: No current track index is set. Cannot save." in captured.out
