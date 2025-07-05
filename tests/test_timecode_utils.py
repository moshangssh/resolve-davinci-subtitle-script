import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import platform
import math

# Add the subvigator directory to the path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from subvigator.timecode_utils import TimecodeUtils

class TestTimecodeUtils(unittest.TestCase):

    @patch('cffi.FFI')
    def setUp(self, mock_ffi):
        """Set up a test instance of TimecodeUtils with mocked dependencies."""
        self.mock_ffi_instance = mock_ffi.return_value
        self.mock_lib = MagicMock()
        self.mock_ffi_instance.dlopen.return_value = self.mock_lib

        # Mock the C struct to have a 'start' attribute
        self.mock_tc = MagicMock()
        self.mock_tc.start = 86400  # Example frame number for 01:00:00:00 at 24fps
        self.mock_ffi_instance.new.side_effect = [self.mock_tc, MagicMock()]


        with patch('platform.system', return_value='Linux'):
            self.utils = TimecodeUtils()

    def test_initialization(self):
        """Test that the class initializes correctly."""
        self.mock_ffi_instance.cdef.assert_called_once()
        self.mock_ffi_instance.dlopen.assert_called_once_with("libavutil.so")
        self.assertIsNotNone(self.utils.libavutil)

    def test_initialization_windows(self):
        """Test library loading on Windows."""
        with patch('platform.system', return_value='Windows'):
            self.utils._load_library()
            self.mock_ffi_instance.dlopen.assert_called_with("avutil-57.dll")

    def test_initialization_darwin(self):
        """Test library loading on macOS."""
        with patch('platform.system', return_value='Darwin'):
            self.utils._load_library()
            self.mock_ffi_instance.dlopen.assert_called_with("libavutil.dylib")

    def test_initialization_library_not_found(self):
        """Test error handling when the library is not found."""
        self.mock_ffi_instance.dlopen.side_effect = OSError("Library not found")
        with self.assertRaises(ImportError) as context:
            with patch('platform.system', return_value='Linux'):
                 TimecodeUtils()
        self.assertIn("Could not load the libavutil.so library", str(context.exception))


    def test_get_frame_rates(self):
        """Test that the list of frame rates is correct."""
        expected_rates = [16, 18, 23.976, 24, 25, 29.97, 30, 47.952, 48, 50, 59.94, 60, 72, 95.904, 96, 100, 119.88, 120]
        self.assertEqual(self.utils.get_frame_rates(), expected_rates)

    def test_get_fraction(self):
        """Test the frame rate to fraction conversion."""
        self.assertEqual(self.utils.get_fraction(24), {'num': 2400, 'den': 100})
        self.assertEqual(self.utils.get_fraction("29.97"), {'num': 30000, 'den': 1001})
        self.assertEqual(self.utils.get_fraction(23.976), {'num': 24000, 'den': 1001})
        with self.assertRaises(ValueError):
            self.utils.get_fraction(15)

    def test_get_decimal(self):
        """Test the fraction to decimal conversion."""
        self.assertAlmostEqual(self.utils.get_decimal(29.97), 29.970, places=3)
        self.assertAlmostEqual(self.utils.get_decimal(24), 24.000, places=3)
        self.assertAlmostEqual(self.utils.get_decimal("23.976"), 23.976, places=3)


    def test_frame_from_timecode_success(self):
        """Test converting a timecode string to a frame number successfully."""
        self.mock_lib.av_timecode_init_from_string.return_value = 0
        frame = self.utils.frame_from_timecode("01:00:00:00", 24)
        self.assertEqual(frame, 86400)
        self.mock_lib.av_timecode_init_from_string.assert_called_once()


    def test_frame_from_timecode_error(self):
        """Test converting a timecode string with an error from the library."""
        self.mock_lib.av_timecode_init_from_string.return_value = -1
        with self.assertRaises(RuntimeError) as context:
            self.utils.frame_from_timecode("invalid", 24)
        self.assertIn("avutil error code: -1", str(context.exception))

    def test_timecode_from_frame(self):
        """Test the placeholder implementation of timecode_from_frame."""
        # This test will need to be updated when the function is fully implemented.
        self.assertEqual(self.utils.timecode_from_frame(86400, 24), "00:00:00:00")

if __name__ == '__main__':
    unittest.main()