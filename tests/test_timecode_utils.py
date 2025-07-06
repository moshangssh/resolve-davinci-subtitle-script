import pytest
from unittest.mock import MagicMock
import os
import platform

# 导入被测试的类
from src.timecode_utils import TimecodeUtils

@pytest.fixture
def mock_resolve():
    """提供一个干净的 resolve mock 对象"""
    resolve = MagicMock()
    fusion = MagicMock()
    resolve.Fusion.return_value = fusion
    fusion.MapPath.return_value = "/fake/fusion/libs"
    return resolve

# 1. 初始化和库加载测试
class TestInitialization:

    @pytest.fixture(autouse=True)
    def patch_dependencies(self, monkeypatch):
        """在每个测试前，独立地 patch 所有外部依赖"""
        self.mock_ffi = MagicMock()
        self.mock_libavutil = MagicMock()
        self.mock_ffi.dlopen.return_value = self.mock_libavutil
        
        self.mock_glob_module = MagicMock()

        monkeypatch.setattr('cffi.FFI', lambda: self.mock_ffi)
        monkeypatch.setattr('src.timecode_utils.glob', self.mock_glob_module)
        self.monkeypatch = monkeypatch

    def test_init_success_windows(self, mock_resolve):
        self.monkeypatch.setattr('platform.system', lambda: "Windows")
        self.mock_glob_module.glob.return_value = ["/fake/fusion/libs/avutil-57.dll"]
        
        utils = TimecodeUtils(mock_resolve)
        
        mock_resolve.Fusion.assert_called_once()
        mock_resolve.Fusion().MapPath.assert_called_once_with("FusionLibs:")
        expected_path = os.path.join("/fake/fusion/libs", "avutil*.dll")
        self.mock_glob_module.glob.assert_called_once_with(expected_path)
        self.mock_ffi.dlopen.assert_called_once_with("/fake/fusion/libs/avutil-57.dll")
        assert utils.libavutil is self.mock_libavutil

    def test_init_success_linux(self, mock_resolve):
        self.monkeypatch.setattr('platform.system', lambda: "Linux")
        self.mock_glob_module.glob.return_value = ["/fake/fusion/libavutil.so"]
        
        utils = TimecodeUtils(mock_resolve)
        
        expected_path = os.path.abspath(os.path.join("/fake/fusion/libs", '..'))
        self.mock_glob_module.glob.assert_called_once_with(os.path.join(expected_path, "libavutil.so"))
        self.mock_ffi.dlopen.assert_called_once_with("/fake/fusion/libavutil.so")

    def test_init_success_darwin(self, mock_resolve):
        self.monkeypatch.setattr('platform.system', lambda: "Darwin")
        self.mock_glob_module.glob.return_value = ["/fake/fusion/libavutil-58.dylib"]
        
        utils = TimecodeUtils(mock_resolve)
        
        expected_path = os.path.abspath(os.path.join("/fake/fusion/libs", '..'))
        self.mock_glob_module.glob.assert_called_once_with(os.path.join(expected_path, "libavutil*.dylib"))
        self.mock_ffi.dlopen.assert_called_once_with("/fake/fusion/libavutil-58.dylib")

    def test_init_no_resolve_object(self):
        with pytest.raises(ImportError, match="Resolve object not provided"):
            TimecodeUtils(None)

    def test_init_no_fusion_object(self, mock_resolve):
        mock_resolve.Fusion.side_effect = AttributeError("Test attribute error")
        with pytest.raises(ImportError, match="Could not get Fusion object"):
            TimecodeUtils(mock_resolve)
    
    def test_init_library_not_found(self, mock_resolve):
        self.monkeypatch.setattr('platform.system', lambda: "Windows")
        self.mock_glob_module.glob.return_value = []
        
        with pytest.raises(ImportError, match="Could not find library"):
            TimecodeUtils(mock_resolve)

    def test_init_library_load_failure(self, mock_resolve):
        self.monkeypatch.setattr('platform.system', lambda: "Windows")
        self.mock_glob_module.glob.return_value = ["/fake/path/avutil.dll"]
        self.mock_ffi.dlopen.side_effect = OSError("Test OS error")
        
        with pytest.raises(ImportError, match="Failed to load"):
            TimecodeUtils(mock_resolve)

# Fixture for a successfully initialized instance for other test classes
@pytest.fixture
def utils_instance(monkeypatch, mock_resolve):
    monkeypatch.setattr('platform.system', lambda: "Windows")
    mock_glob_module = MagicMock()
    mock_glob_module.glob.return_value = ["/fake/path/avutil.dll"]
    mock_ffi = MagicMock()
    mock_ffi.dlopen.return_value = MagicMock()
    
    monkeypatch.setattr('src.timecode_utils.glob', mock_glob_module)
    monkeypatch.setattr('cffi.FFI', lambda: mock_ffi)
    
    return TimecodeUtils(mock_resolve)

# 2. 帧率转换函数测试
class TestFrameRateConversion:
    @pytest.mark.parametrize("rate_in, expected_frac", [
        (24, {'num': 2400, 'den': 100}),
        ("23.976", {'num': 24000, 'den': 1001}),
        (29.97, {'num': 30000, 'den': 1001}),
    ])
    def test_get_fraction_valid(self, utils_instance, rate_in, expected_frac):
        assert utils_instance.get_fraction(rate_in) == expected_frac

    def test_get_fraction_invalid(self, utils_instance):
        with pytest.raises(ValueError, match="Invalid frame rate"):
            utils_instance.get_fraction(999)

    def test_get_decimal(self, utils_instance):
        assert utils_instance.get_decimal(29.97) == 29.970

# 3. 时间码/帧核心转换逻辑测试
class TestTimecodeFrameConversion:
    def test_frame_from_timecode_success(self, utils_instance):
        mock_tc = MagicMock()
        mock_tc.start = 108000
        utils_instance.ffi.new.return_value = mock_tc
        utils_instance.libavutil.av_timecode_init_from_string.return_value = 0
        
        frame = utils_instance.frame_from_timecode("01:00:00:00", 30)
        assert frame == 108000

    def test_frame_from_timecode_failure(self, utils_instance):
        utils_instance.libavutil.av_timecode_init_from_string.return_value = -1
        with pytest.raises(RuntimeError):
            utils_instance.frame_from_timecode("invalid", 30)

    def test_timecode_from_frame_success(self, utils_instance):
        utils_instance.ffi.string.return_value = b"01:00:00:00"
        utils_instance.libavutil.av_timecode_make_string.return_value = "non-NULL"
        
        timecode = utils_instance.timecode_from_frame(108000, 30)
        assert timecode == "01:00:00:00"

    def test_timecode_from_frame_drop_frame(self, utils_instance):
        utils_instance.timecode_from_frame(107892, 29.97, drop_frame=True)
        
        av_timecode_call = None
        for call in utils_instance.ffi.new.call_args_list:
            # 确保我们找到的是带有初始化字典的调用
            if len(call.args) > 1 and isinstance(call.args[1], dict):
                av_timecode_call = call
                break
        
        assert av_timecode_call is not None, "ffi.new was not called with initializer dict"
        
        flags = av_timecode_call.args[1]['flags']
        assert flags & 1  # AV_TIMECODE_FLAG_DROPFRAME
        assert flags & 2  # AV_TIMECODE_FLAG_24HOURSMAX

    def test_timecode_from_frame_failure(self, utils_instance):
        utils_instance.libavutil.av_timecode_make_string.return_value = utils_instance.ffi.NULL
        timecode = utils_instance.timecode_from_frame(0, 30)
        assert timecode == "00:00:00:00"
