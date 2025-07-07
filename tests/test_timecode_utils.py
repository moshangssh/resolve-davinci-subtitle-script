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
    with pytest.raises(ImportError):
        TimecodeUtils(None)

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
    with pytest.raises(RuntimeError):
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
    with pytest.raises(ValueError):
        utils.get_fraction(999)
