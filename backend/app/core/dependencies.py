from functools import lru_cache
from ..services.subtitle_manager import SubtitleManager

@lru_cache(maxsize=1)
def get_subtitle_manager() -> SubtitleManager:
    """
    获取 SubtitleManager 的单例实例。

    使用 @lru_cache(maxsize=1) 装饰器可以非常方便地实现单例模式。
    当这个函数第一次被调用时，它会创建一个 SubtitleManager 实例并返回。
    之后所有的调用都会直接返回这个缓存的实例，而不会再创建新的实例。

    Returns:
        SubtitleManager: 字幕管理器的唯一实例。
    """
    # 在这里可以进行一些初始化工作，例如传入配置
    # from app.core.config import settings
    # return SubtitleManager(some_setting=settings.SOME_VALUE)
    return SubtitleManager()
