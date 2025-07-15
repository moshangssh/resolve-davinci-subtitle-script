# tests/test_timecode_utils.py
import pytest
from unittest.mock import MagicMock, patch
from src.timecode_utils import TimecodeUtils

@pytest.fixture
def mock_cffi(mocker):
    """Fixture to mock the cffi library."""
    mock_ffi = MagicMock()
    mock_libavutil = MagicMock()
    mock_ffi.dlopen.return_value = mock_libavutil
    mocker.patch('src.timecode_utils.cffi.FFI', return_value=mock_ffi)
    return {"ffi": mock_ffi, "libavutil": mock_libavutil}

@pytest.fixture
def mock_resolve(mocker):
    """Fixture to mock the Resolve object."""
    mock_res = MagicMock()
    mock_fusion = MagicMock()
    mock_res.Fusion.return_value = mock_fusion
    mock_fusion.MapPath.return_value = "/fake/path"
    mocker.patch('src.timecode_utils.glob.glob', return_value=["/fake/path/libavutil.so"])
    return mock_res

def test_timecode_utils_init_success(mock_resolve, mock_cffi):
    """Test successful initialization of TimecodeUtils."""
    utils = TimecodeUtils(mock_resolve)
    assert utils.resolve is not None
    assert utils.ffi is not None
    assert utils.libavutil is not None

def test_timecode_utils_init_no_resolve():
    """Test initialization without a Resolve object."""
    utils = TimecodeUtils(None)
    assert utils.resolve is None
    assert utils.ffi is None
    assert utils.libavutil is None

def test_timecode_from_frame_success(mock_resolve, mock_cffi):
    """Test timecode_from_frame."""
    mock_cffi["ffi"].string.return_value.decode.return_value = "00:00:01:00"
    utils = TimecodeUtils(mock_resolve)
    tc = utils.timecode_from_frame(24, 24)
    assert tc == "00:00:01:00"

def test_frame_from_timecode_success(mock_resolve, mock_cffi):
    """Test frame_from_timecode."""
    mock_tc_struct = MagicMock()
    mock_tc_struct.start = 24
    mock_cffi["ffi"].new.side_effect = [mock_tc_struct, MagicMock()] # for AVTimecode and AVRational
    mock_cffi["libavutil"].av_timecode_init_from_string.return_value = 0
    
    utils = TimecodeUtils(mock_resolve)
    frame = utils.frame_from_timecode("00:00:01:00", 24)
    assert frame == 24

def test_frame_from_timecode_error(mock_resolve, mock_cffi):
    """Test frame_from_timecode with an avutil error."""
    mock_cffi["libavutil"].av_timecode_init_from_string.return_value = -1
    utils = TimecodeUtils(mock_resolve)
    with pytest.raises(ValueError, match="Invalid timecode format: invalid"):
        utils.frame_from_timecode("invalid", 24)

def test_get_decimal(mock_resolve, mock_cffi):
    """Test get_decimal."""
    utils = TimecodeUtils(mock_resolve)
    assert utils.get_decimal(23.976) == 23.976

def test_get_fraction(mock_resolve, mock_cffi):
    """Test get_fraction."""
    utils = TimecodeUtils(mock_resolve)
    frac = utils.get_fraction(29.97)
    assert frac['num'] == 30000
    assert frac['den'] == 1001

def test_get_fraction_invalid_rate(mock_resolve, mock_cffi):
    """Test get_fraction with an invalid frame rate."""
    utils = TimecodeUtils(mock_resolve)
    with pytest.raises(ValueError, match="Invalid frame rate: 999"):
        utils.get_fraction(999)

def test_get_fraction_invalid_format(mock_resolve, mock_cffi):
    """Test get_fraction with a non-numeric frame rate."""
    utils = TimecodeUtils(mock_resolve)
    with pytest.raises(ValueError, match="Invalid frame rate format: abc"):
        utils.get_fraction("abc")

def test_timecode_to_srt_format_negative_frame():
    """Test timecode_to_srt_format with a negative frame number."""
    # This should be handled gracefully, returning the same as frame 0
    assert TimecodeUtils.timecode_to_srt_format(-100, 24) == "00:00:00,000"

def test_timecode_from_frame_negative_input(mock_resolve, mock_cffi):
    """Test timecode_from_frame with a negative frame number."""
    mock_cffi["ffi"].string.return_value.decode.return_value = "00:00:00:00"
    utils = TimecodeUtils(mock_resolve)
    # The function should treat negative frame as 0
    tc = utils.timecode_from_frame(-10, 24)
    assert tc == "00:00:00:00"
    # Check that the C function was called with 0
    mock_cffi["libavutil"].av_timecode_make_string.assert_called()
    # Get the arguments of the last call
    args, _ = mock_cffi["libavutil"].av_timecode_make_string.call_args
    # The frame number is the 3rd argument (index 2)
    assert args[2] == 0

@patch('src.timecode_utils.glob.glob')
@patch('src.timecode_utils.logging')
def test_load_library_selects_highest_version(mock_logging, mock_glob, mock_resolve, mock_cffi):
    """Test that _load_library selects the library with the highest version."""
    mock_glob.return_value = ["/fake/path/avutil-57.dll", "/fake/path/avutil-58.dll"]
    mock_lib_58 = MagicMock()
    mock_lib_58.name = "avutil-58.dll"
    mock_cffi["ffi"].dlopen.return_value = mock_lib_58
    
    utils = TimecodeUtils(mock_resolve)

    mock_cffi["ffi"].dlopen.assert_called_with("/fake/path/avutil-58.dll")
    assert utils.libavutil.name == "avutil-58.dll"
    mock_logging.info.assert_any_call("Selected library with highest version: /fake/path/avutil-58.dll")

@patch('src.timecode_utils.glob.glob')
@patch('src.timecode_utils.logging')
def test_load_library_version_parse_warning(mock_logging, mock_glob, mock_resolve, mock_cffi):
    """Test that a warning is logged for unparsable library versions."""
    mock_glob.return_value = ["/fake/path/avutil-58.dll", "/fake/path/avutil-bad.dll"]
    mock_lib_58 = MagicMock()
    mock_lib_58.name = "avutil-58.dll"
    mock_cffi["ffi"].dlopen.return_value = mock_lib_58

    utils = TimecodeUtils(mock_resolve)

    mock_cffi["ffi"].dlopen.assert_called_with("/fake/path/avutil-58.dll")
    assert utils.libavutil.name == "avutil-58.dll"
    mock_logging.warning.assert_any_call("Could not parse version from '/fake/path/avutil-bad.dll'.")

@patch('src.timecode_utils.glob.glob')
@patch('src.timecode_utils.logging')
def test_load_library_fallback_on_no_version(mock_logging, mock_glob, mock_resolve, mock_cffi):
    """Test that _load_library falls back to the first lib if no versions can be parsed."""
    mock_glob.return_value = ["/fake/path/avutil-foo.dll", "/fake/path/avutil-bar.dll"]
    mock_lib_foo = MagicMock()
    mock_lib_foo.name = "avutil-foo.dll"
    mock_cffi["ffi"].dlopen.return_value = mock_lib_foo
    
    utils = TimecodeUtils(mock_resolve)

    mock_cffi["ffi"].dlopen.assert_called_with("/fake/path/avutil-foo.dll")
    assert utils.libavutil.name == "avutil-foo.dll"
    mock_logging.warning.assert_any_call("Could not determine the best library version. Falling back to the first one found.")

@patch('src.timecode_utils.glob.glob')
@patch('src.timecode_utils.logging')
def test_load_library_logs_loading_path(mock_logging, mock_glob, mock_resolve, mock_cffi):
    """Test that _load_library logs the path of the library it's attempting to load."""
    mock_glob.return_value = ["/fake/path/avutil-58.dll"]
    
    utils = TimecodeUtils(mock_resolve)
    
    mock_logging.info.assert_any_call("Attempting to load library from DaVinci Resolve's path: /fake/path/avutil-58.dll")
