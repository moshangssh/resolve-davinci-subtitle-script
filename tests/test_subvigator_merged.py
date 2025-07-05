import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os
import platform
from PySide6.QtWidgets import QApplication, QLineEdit, QComboBox, QTreeWidget, QPushButton
from PySide6.QtCore import Qt

# Since the original classes are in a merged file, we need to import them.
# This assumes the subvigator_merged.py is in the parent directory of tests/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from subvigator_merged import TimecodeUtils, ResolveIntegration, ApplicationController, SubvigatorWindow

# New test class specifically for the library loading logic
class TestTimecodeUtilsLoading(unittest.TestCase):

    def setUp(self):
        # Mock resolve object for initialization
        self.mock_resolve = MagicMock()
        self.mock_fusion = MagicMock()
        self.mock_resolve.Fusion.return_value = self.mock_fusion
        self.mock_fusion.MapPath.return_value = "/fake/fusion/libs"

    def test_init_no_resolve_object(self):
        """5. `__init__` 失败 - 未提供 resolve 对象"""
        with self.assertRaises(ImportError) as cm:
            # We need to patch _define_c_types and ffi to avoid errors during init
            with patch.object(TimecodeUtils, '_define_c_types'), \
                 patch('cffi.FFI'):
                TimecodeUtils(None)
        self.assertIn("Resolve object not provided", str(cm.exception))

    def test_load_library_no_fusion_object(self):
        """6. `_load_library` 失败 - 无法获取 Fusion 对象"""
        # Unset the Fusion method
        del self.mock_resolve.Fusion
        
        with self.assertRaises(ImportError) as cm:
            with patch.object(TimecodeUtils, '_define_c_types'), \
                 patch('cffi.FFI'):
                TimecodeUtils(self.mock_resolve)
        self.assertIn("Could not get Fusion object", str(cm.exception))

    @patch('platform.system', return_value='Linux')
    @patch('glob.glob')
    @patch('os.path.abspath')
    @patch('cffi.FFI')
    def test_load_library_linux_path(self, mock_ffi_class, mock_abspath, mock_glob, mock_system):
        """7. `_load_library` 成功 - Linux 路径"""
        # Arrange
        mock_ffi_instance = mock_ffi_class.return_value
        self.mock_fusion.MapPath.return_value = "/some/path/FusionLibs"
        mock_abspath.return_value = "/some/path"
        mock_glob.return_value = ['/some/path/libavutil.so']

        # Act
        TimecodeUtils(self.mock_resolve)

        # Assert
        self.mock_fusion.MapPath.assert_called_with("FusionLibs:")
        mock_abspath.assert_called_once_with(os.path.join("/some/path/FusionLibs", '..'))
        mock_glob.assert_called_with(os.path.join("/some/path", "libavutil.so"))
        mock_ffi_instance.dlopen.assert_called_with('/some/path/libavutil.so')


    @patch('platform.system', return_value='Windows')
    @patch('glob.glob', return_value=['/fake/fusion/libs/avutil-58.dll'])
    @patch('cffi.FFI')
    def test_load_library_success(self, mock_ffi_class, mock_glob, mock_system):
        """
        1. `_load_library` 成功加载
        """
        mock_ffi_instance = mock_ffi_class.return_value
        mock_lib = MagicMock()
        mock_ffi_instance.dlopen.return_value = mock_lib

        # Instantiate the class, which triggers _load_library
        timecode_utils = TimecodeUtils(self.mock_resolve)

        # Assertions
        mock_glob.assert_called_once_with("/fake/fusion/libs\\avutil*.dll")
        mock_ffi_instance.dlopen.assert_called_with('/fake/fusion/libs/avutil-58.dll')
        self.assertIsNotNone(timecode_utils.libavutil)
        self.assertEqual(timecode_utils.libavutil, mock_lib)

    @patch('platform.system', return_value='Windows')
    @patch('glob.glob', return_value=[]) # Simulate library not found
    @patch('cffi.FFI')
    def test_load_library_not_found_failure(self, mock_ffi_class, mock_glob, mock_system):
        """
        2. `_load_library` 加载失败 - 找不到库
        """
        with self.assertRaises(ImportError) as cm:
            TimecodeUtils(self.mock_resolve)
        self.assertIn("Could not find library", str(cm.exception))

    @patch('platform.system', return_value='Darwin')
    @patch('glob.glob', return_value=['/fake/fusion/libs/libavutil.58.dylib'])
    @patch('cffi.FFI')
    def test_load_library_dlopen_failure(self, mock_ffi_class, mock_glob, mock_system):
        """
        3. `_load_library` 加载失败 - `dlopen` 异常
        """
        mock_ffi_instance = mock_ffi_class.return_value
        mock_ffi_instance.dlopen.side_effect = OSError("dlopen failed")

        with self.assertRaises(ImportError) as cm:
            TimecodeUtils(self.mock_resolve)
        self.assertIn("Failed to load", str(cm.exception))
        self.assertIn("dlopen failed", str(cm.exception))

    @patch('subvigator_merged.TimecodeUtils._load_library')
    def test_init_calls_load_library(self, mock_load_library):
        """
        4. `__init__` 初始化
        """
        mock_load_library.return_value = MagicMock()
        # Pass a mock resolve object during initialization
        timecode_utils = TimecodeUtils(MagicMock())
        mock_load_library.assert_called_once()


class TestTimecodeUtils(unittest.TestCase):
    def setUp(self):
        # We patch the library loading to avoid actual CFFI dependency in these tests.
        # The loading itself is tested in TestTimecodeUtilsLoading.
        with patch.object(TimecodeUtils, '_load_library', return_value=MagicMock()):
             # We need to pass a mock resolve object here.
            self.timecode_utils = TimecodeUtils(resolve=MagicMock())


    def test_get_fraction(self):
        self.assertEqual(self.timecode_utils.get_fraction(24), {'num': 2400, 'den': 100})
        self.assertEqual(self.timecode_utils.get_fraction(23.976), {'num': 24000, 'den': 1001})
        with self.assertRaises(ValueError):
            self.timecode_utils.get_fraction(999)

    def test_get_decimal(self):
        self.assertAlmostEqual(self.timecode_utils.get_decimal(23.976), 23.976, places=3)
        self.assertAlmostEqual(self.timecode_utils.get_decimal(30), 30.0, places=3)

    @patch('cffi.FFI')
    def test_frame_from_timecode(self, mock_ffi_class):
        # This test is more complex due to CFFI. We'll mock the C-level interaction.
        mock_ffi_instance = mock_ffi_class.return_value
        mock_lib = MagicMock()
        mock_tc = MagicMock()
        
        # Simulate successful call
        mock_tc.start = 12345
        mock_lib.av_timecode_init_from_string.return_value = 0
        # Correct order: tc is created first, then rate.
        mock_ffi_instance.new.side_effect = [mock_tc, MagicMock()]

        self.timecode_utils.ffi = mock_ffi_instance
        self.timecode_utils.libavutil = mock_lib
        
        frame = self.timecode_utils.frame_from_timecode("00:00:08:10", 24)
        self.assertEqual(frame, 12345)

    @patch('cffi.FFI')
    def test_frame_from_timecode_error(self, mock_ffi_class):
        mock_ffi_instance = mock_ffi_class.return_value
        mock_lib = MagicMock()
        mock_ffi_instance.new.side_effect = [MagicMock(), MagicMock()]
        mock_lib.av_timecode_init_from_string.return_value = -1
        self.timecode_utils.ffi = mock_ffi_instance
        self.timecode_utils.libavutil = mock_lib
        with self.assertRaises(RuntimeError):
            self.timecode_utils.frame_from_timecode("invalid", 24)

    def test_timecode_from_frame(self):
        # The original function is a placeholder, so we test its placeholder behavior
        self.assertEqual(self.timecode_utils.timecode_from_frame(100, 24), "00:00:00:00")

class TestResolveIntegration(unittest.TestCase):

    @patch('subvigator_merged.ResolveIntegration._get_resolve_instance')
    def setUp(self, mock_get_resolve):
        self.mock_resolve = MagicMock()
        self.mock_project_manager = MagicMock()
        self.mock_project = MagicMock()
        self.mock_timeline = MagicMock()

        mock_get_resolve.return_value = self.mock_resolve
        self.mock_resolve.GetProjectManager.return_value = self.mock_project_manager
        self.mock_project_manager.GetCurrentProject.return_value = self.mock_project
        self.mock_project.GetCurrentTimeline.return_value = self.mock_timeline
        
        self.resolve_integration = ResolveIntegration()

    def test_init_success(self):
        self.assertIsNotNone(self.resolve_integration.resolve)
        self.assertIsNotNone(self.resolve_integration.project_manager)
        self.assertIsNotNone(self.resolve_integration.project)
        self.assertIsNotNone(self.resolve_integration.timeline)

    @patch('subvigator_merged.ResolveIntegration._get_resolve_instance', return_value=None)
    def test_init_failure(self, mock_get_resolve):
        with self.assertRaises(ImportError):
            ResolveIntegration()

    def test_get_current_timeline_info(self):
        self.mock_timeline.GetSetting.return_value = 24
        type(self.mock_timeline).GetTrackCount = MagicMock(return_value=2)
        
        info = self.resolve_integration.get_current_timeline_info()
        
        self.assertEqual(info['frame_rate'], 24)
        self.assertEqual(info['track_count'], 2)
        
        # Test case where timeline is None
        self.resolve_integration.timeline = None
        self.assertIsNone(self.resolve_integration.get_current_timeline_info())

    def test_get_subtitles(self):
        mock_sub1 = MagicMock()
        mock_sub2 = MagicMock()
        self.mock_timeline.GetItemListInTrack.return_value = [mock_sub1, mock_sub2]
        
        subs = self.resolve_integration.get_subtitles(1)
        
        self.assertEqual(len(subs), 2)
        self.mock_timeline.GetItemListInTrack.assert_called_with('subtitle', 1)

        # Test case where timeline is None
        self.resolve_integration.timeline = None
        self.assertEqual(self.resolve_integration.get_subtitles(), [])


class TestResolveInstanceLoading(unittest.TestCase):
    @patch('importlib.import_module')
    def test_get_resolve_instance_fusionscript_success(self, mock_import):
        """Test _get_resolve_instance with fusionscript succeeding."""
        mock_fusionscript = MagicMock()
        mock_fusionscript.scriptapp.return_value = "FusionSuccess"
        mock_import.side_effect = lambda name: {'fusionscript': mock_fusionscript}[name]

        instance = ResolveIntegration._get_resolve_instance(None)
        self.assertEqual(instance, "FusionSuccess")

    @patch('importlib.import_module')
    def test_get_resolve_instance_fallback_success(self, mock_import):
        """Test _get_resolve_instance falling back to DaVinciResolveScript."""
        mock_dvr_script = MagicMock()
        mock_dvr_script.scriptapp.return_value = "DVRSuccess"
        def import_side_effect(name):
            if name == 'fusionscript':
                raise ImportError
            elif name == 'DaVinciResolveScript':
                return mock_dvr_script
        mock_import.side_effect = import_side_effect

        instance = ResolveIntegration._get_resolve_instance(None)
        self.assertEqual(instance, "DVRSuccess")

    @patch('importlib.import_module', side_effect=ImportError)
    def test_get_resolve_instance_all_fail(self, mock_import):
        """Test _get_resolve_instance when both imports fail."""
        instance = ResolveIntegration._get_resolve_instance(None)
        self.assertIsNone(instance)


class TestSubvigatorWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # QApplication instance is required for widget creation
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.window = SubvigatorWindow()

    def test_widgets_created(self):
        self.assertIsInstance(self.window.search_text, QLineEdit)
        self.assertIsInstance(self.window.track_combo, QComboBox)
        self.assertIsInstance(self.window.tree, QTreeWidget)
        self.assertIsInstance(self.window.refresh_button, QPushButton)

    def test_populate_table(self):
        mock_sub1 = MagicMock()
        mock_sub1.GetName.return_value = "Sub 1"
        mock_sub1.GetStart.return_value = 100
        mock_sub2 = MagicMock()
        mock_sub2.GetName.return_value = "Sub 2"
        mock_sub2.GetStart.return_value = 200

        subs_data = {1: mock_sub1, 2: mock_sub2}
        
        with patch.object(self.window.tree, 'sortItems') as mock_sort:
            self.window.populate_table(subs_data)
            self.assertEqual(self.window.tree.topLevelItemCount(), 2)
            item1 = self.window.tree.topLevelItem(0)
            self.assertEqual(item1.text(0), "1")
            self.assertEqual(item1.text(1), "Sub 1")
            self.assertEqual(item1.text(2), "100")
            mock_sort.assert_called_once_with(0, Qt.AscendingOrder)

    def test_populate_table_with_hide(self):
        mock_sub1 = MagicMock()
        mock_sub1.GetName.return_value = "Sub 1"
        mock_sub1.GetStart.return_value = 100
        subs_data = {1: mock_sub1}
        
        self.window.populate_table(subs_data, hide=True)
        
        item = self.window.tree.topLevelItem(0)
        self.assertTrue(item.isHidden())

    def tearDown(self):
        self.window.close()

class TestApplicationController(unittest.TestCase):

    @patch('subvigator_merged.QApplication')
    @patch('subvigator_merged.ResolveIntegration')
    @patch('subvigator_merged.TimecodeUtils')
    @patch('subvigator_merged.SubvigatorWindow')
    def setUp(self, mock_window_class, mock_timecode_utils, mock_resolve_integration, mock_qapp):
        # Mock the backend classes
        self.mock_resolve = mock_resolve_integration.return_value
        self.mock_timecode = mock_timecode_utils.return_value
        
        # Mock the UI window instance
        self.mock_window = mock_window_class.return_value
        
        # Instantiate the controller
        self.controller = ApplicationController()

    def test_init_controller(self):
        self.assertIsNotNone(self.controller.resolve_integration)
        self.assertIsNotNone(self.controller.timecode_utils)
        self.assertIsNotNone(self.controller.window)
        self.controller.window.show.assert_not_called() # Should not be shown yet

    def test_init_controller_resolve_fails(self):
        # Test the except block in __init__
        with patch('subvigator_merged.ResolveIntegration', side_effect=ImportError("Test Resolve Error")), \
             patch('sys.exit') as mock_exit:
            
            controller = ApplicationController()
            mock_exit.assert_called_once_with(1)
            
    def test_refresh_data_no_timeline(self):
        # Test the case where get_current_timeline_info returns None
        self.mock_resolve.get_current_timeline_info.return_value = None
        self.controller.refresh_data()
        self.mock_window.track_combo.clear.assert_not_called()

    def test_refresh_data(self):
        # Setup mock data from Resolve
        mock_timeline_info = {'track_count': 3, 'frame_rate': 24}
        self.mock_resolve.get_current_timeline_info.return_value = mock_timeline_info
        
        mock_sub1 = MagicMock()
        mock_sub1.GetName.return_value = "Hello"
        mock_sub2 = MagicMock()
        mock_sub2.GetName.return_value = "World"
        self.mock_resolve.get_subtitles.return_value = [mock_sub1, mock_sub2]

        # Mock UI state
        self.mock_window.track_combo.currentIndex.return_value = 0

        # Call the method
        self.controller.refresh_data()

        # Assertions
        self.mock_window.track_combo.clear.assert_called_once()
        self.assertEqual(self.mock_window.track_combo.addItem.call_count, 3)
        self.mock_resolve.get_subtitles.assert_called_with(1)
        self.mock_window.populate_table.assert_called_once()
        # The argument passed to populate_table is a dictionary of MagicMock objects.
        # We can check the keys and types.
        call_args = self.mock_window.populate_table.call_args[0][0]
        self.assertEqual(len(call_args), 2)
        self.assertEqual(list(call_args.keys()), [1, 2])
        self.assertIsInstance(call_args[1], MagicMock)


    def test_filter_subtitles(self):
        # Mock the tree widget in the window
        mock_item1 = MagicMock()
        mock_item1.text.return_value = "Subtitle One"
        mock_item2 = MagicMock()
        mock_item2.text.return_value = "Another Sub"
        
        self.mock_window.tree.topLevelItemCount.return_value = 2
        self.mock_window.tree.topLevelItem.side_effect = [mock_item1, mock_item2]
        self.mock_window.search_text.text.return_value = "one"
        
        self.controller.filter_subtitles()

        mock_item1.setHidden.assert_called_with(False)
        mock_item2.setHidden.assert_called_with(True)

    def test_filter_subtitles_empty_search(self):
        # Mock the tree widget in the window
        mock_item1 = MagicMock()
        mock_item2 = MagicMock()
        
        self.mock_window.tree.topLevelItemCount.return_value = 2
        self.mock_window.tree.topLevelItem.side_effect = [mock_item1, mock_item2]
        self.mock_window.search_text.text.return_value = ""

        self.controller.filter_subtitles()

        mock_item1.setHidden.assert_called_with(False)
        mock_item2.setHidden.assert_called_with(False)

    def test_on_item_clicked(self):
        # Mock the item and timeline info
        mock_item = MagicMock()
        mock_item.text.return_value = "120" # Start frame
        self.mock_resolve.get_current_timeline_info.return_value = {'frame_rate': 24}
        self.mock_window.drop_frame_checkbox.isChecked.return_value = False
        self.mock_timecode.timecode_from_frame.return_value = "00:00:05:00"

        # Call the method
        self.controller.on_item_clicked(mock_item, 2)

        # Assertions
        self.mock_timecode.timecode_from_frame.assert_called_with(120, 24, False)
        # We can't easily test the print, but we know the core logic was called.

    def test_on_item_clicked_no_start_frame(self):
        mock_item = MagicMock()
        mock_item.text.return_value = "" # No start frame
        self.controller.on_item_clicked(mock_item, 2)
        self.mock_timecode.timecode_from_frame.assert_not_called()
        
    def test_on_item_clicked_drop_frame(self):
        mock_item = MagicMock()
        mock_item.text.return_value = "120"
        self.mock_resolve.get_current_timeline_info.return_value = {'frame_rate': 29.97}
        self.mock_window.drop_frame_checkbox.isChecked.return_value = True # Test DF
        
        self.controller.on_item_clicked(mock_item, 2)
        
        self.mock_timecode.timecode_from_frame.assert_called_with(120, 29.97, True)

    def test_run_method(self):
        # Mock sys.exit to prevent the test runner from exiting
        with patch('sys.exit') as mock_exit:
            self.controller.run()
            self.mock_window.show.assert_called_once()
            self.controller.app.exec.assert_called_once()
            mock_exit.assert_called_once()

@patch('subvigator_merged.ApplicationController')
def test_main_function(mock_controller_class):
    """
    Test the main() function.
    """
    from subvigator_merged import main
    mock_instance = mock_controller_class.return_value

    main()

    mock_controller_class.assert_called_once()
    mock_instance.run.assert_called_once()


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)