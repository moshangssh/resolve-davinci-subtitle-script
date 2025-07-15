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

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_load_subtitles_cache_miss(self, mock_json_dump, mock_file_open, mock_path_exists, mock_makedirs, subtitle_manager, mock_dependencies):
        """Test loading subtitles from Resolve when cache is missed."""
        
        def path_exists_side_effect(path):
            # First call is for the directory, second for the file
            if path == subtitle_manager.cache_dir:
                return False  # Simulate cache directory does not exist
            return False  # Simulate cache file does not exist

        mock_path_exists.side_effect = path_exists_side_effect
        
        resolve_integration = mock_dependencies
        track_index = 1
        mock_subs = [
            {'index': 1, 'text': 'Hello from Resolve'}
        ]
        resolve_integration.export_subtitles_to_json.return_value = mock_subs

        loaded_data = subtitle_manager.load_subtitles(track_index)

        mock_makedirs.assert_called_once_with(subtitle_manager.cache_dir)
        
        expected_file_path = os.path.join(subtitle_manager.cache_dir, f"track_{track_index}.json")
        mock_file_open.assert_called_once_with(expected_file_path, 'w', encoding='utf-8')
        mock_json_dump.assert_called_once_with(mock_subs, mock_file_open(), ensure_ascii=False, indent=2)
        assert loaded_data == mock_subs

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open')
    def test_load_subtitles_cache_hit(self, mock_file_open, mock_path_exists, subtitle_manager, mock_dependencies):
        """Test loading subtitles from an existing cache file."""
        resolve_integration = mock_dependencies
        track_index = 1
        mock_subs_json = json.dumps([
            {'index': 1, 'text': 'Cached Hello'}
        ])
        mock_file_open.return_value = mock_open(read_data=mock_subs_json).return_value

        loaded_data = subtitle_manager.load_subtitles(track_index)

        expected_path = os.path.join(subtitle_manager.cache_dir, f"track_{track_index}.json")
        mock_path_exists.assert_called_with(expected_path)
        resolve_integration.export_subtitles_to_json.assert_not_called()
        assert loaded_data[0]['text'] == 'Cached Hello'

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
        assert "Error: No current track index or json path is set. Cannot save." in captured.out

    @patch('src.subtitle_manager.parse_srt_content')
    def test_load_subtitles_from_valid_srt_content(self, mock_parse_srt, subtitle_manager):
        """Test loading subtitles from a valid SRT content string."""
        srt_content = "1\n00:00:01,000 --> 00:00:02,000\nHello World"
        mock_parsed_data = [{'index': 1, 'start': '00:00:01,000', 'end': '00:00:02,000', 'text': 'Hello World'}]
        mock_parse_srt.return_value = mock_parsed_data
        
        # Mock the save method to avoid actual file I/O in this unit test
        with patch.object(subtitle_manager, '_save_changes_to_json') as mock_save:
            result = subtitle_manager.load_subtitles_from_srt_content(srt_content)
            
            mock_parse_srt.assert_called_once_with(srt_content)
            assert subtitle_manager.subtitles_data == mock_parsed_data
            assert subtitle_manager.is_dirty is True
            assert subtitle_manager.current_track_index == 0
            assert subtitle_manager.current_json_path == os.path.join(subtitle_manager.cache_dir, 'imported_srt.json')
            mock_save.assert_called_once()
            assert result == mock_parsed_data

    @patch('src.subtitle_manager.parse_srt_content')
    def test_load_subtitles_from_srt_creates_cache_file(self, mock_parse_srt, subtitle_manager):
        """Test that loading from SRT content creates a cache file."""
        srt_content = "1\n00:00:03,000 --> 00:00:04,000\nTesting file creation"
        mock_parsed_data = [{'index': 1, 'start': '00:00:03,000', 'end': '00:00:04,000', 'text': 'Testing file creation'}]
        mock_parse_srt.return_value = mock_parsed_data
        
        m_open = mock_open()
        with patch('builtins.open', m_open), patch('json.dump') as mock_json_dump:
            subtitle_manager.load_subtitles_from_srt_content(srt_content)

            expected_path = os.path.join(subtitle_manager.cache_dir, 'imported_srt.json')
            m_open.assert_called_once_with(expected_path, 'w', encoding='utf-8')
            
            # The data saved is cleaned, so we expect 'text' to be cleaned
            expected_data_to_save = [{'index': 1, 'start': '00:00:03,000', 'end': '00:00:04,000', 'text': 'Testing file creation'}]
            mock_json_dump.assert_called_once_with(expected_data_to_save, m_open(), ensure_ascii=False, indent=2)

    @patch('src.subtitle_manager.parse_srt_content')
    def test_load_subtitles_from_empty_srt_content(self, mock_parse_srt, subtitle_manager):
        """Test loading subtitles from an empty or invalid SRT content string."""
        srt_content = ""
        mock_parse_srt.return_value = []
        
        with patch.object(subtitle_manager, '_save_changes_to_json') as mock_save:
            result = subtitle_manager.load_subtitles_from_srt_content(srt_content)
            
            mock_parse_srt.assert_called_once_with(srt_content)
            assert result == []
            assert subtitle_manager.subtitles_data == [] # Assuming it was initially empty
            mock_save.assert_not_called()
