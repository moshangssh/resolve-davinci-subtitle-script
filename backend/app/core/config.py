from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets

class Settings(BaseSettings):
    """
    应用配置类，使用 Pydantic-Settings 从环境变量中加载配置。
    """
    # API 安全令牌，用于保护本地 API 不被恶意网页脚本调用
    # 在启动时生成一个高熵的随机字符串
    API_TOKEN: str = secrets.token_hex(32)

    # 日志级别
    LOG_LEVEL: str = "INFO"

    # Pydantic-Settings 的配置
    model_config = SettingsConfigDict(
        # 环境变量文件路径
        env_file=".env",
        # 环境变量文件编码
        env_file_encoding="utf-8",
        # 允许额外的字段
        extra="ignore"
    )

# 创建一个全局的配置实例，方便在其他模块中导入和使用
settings = Settings()
