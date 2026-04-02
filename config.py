# config.py
# 全局配置 - 从原项目直接复用，三组共用同一份
# 原始文件：BettaFish/config.py

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

PROJECT_ROOT: Path = Path(__file__).resolve().parent
CWD_ENV: Path = Path.cwd() / ".env"
ENV_FILE: str = str(CWD_ENV if CWD_ENV.exists() else (PROJECT_ROOT / ".env"))


class Settings(BaseSettings):
    model_config = {"env_file": ENV_FILE, "env_file_encoding": "utf-8", "extra": "ignore"}

    HOST: str = Field("0.0.0.0")
    PORT: int = Field(5000)

    DB_DIALECT: str = Field("postgresql")
    DB_HOST: str = Field("your_db_host")
    DB_PORT: int = Field(3306)
    DB_USER: str = Field("your_db_user")
    DB_PASSWORD: str = Field("your_db_password")
    DB_NAME: str = Field("your_db_name")
    DB_CHARSET: str = Field("utf8mb4")

    INSIGHT_ENGINE_API_KEY: Optional[str] = Field(None)
    INSIGHT_ENGINE_BASE_URL: Optional[str] = Field("https://api.moonshot.cn/v1")
    INSIGHT_ENGINE_MODEL_NAME: str = Field("kimi-k2-0711-preview")

    MEDIA_ENGINE_API_KEY: Optional[str] = Field(None)
    MEDIA_ENGINE_BASE_URL: Optional[str] = Field("https://aihubmix.com/v1")
    MEDIA_ENGINE_MODEL_NAME: str = Field("gemini-2.5-pro")

    QUERY_ENGINE_API_KEY: Optional[str] = Field(None)
    QUERY_ENGINE_BASE_URL: Optional[str] = Field("https://api.deepseek.com")
    QUERY_ENGINE_MODEL_NAME: str = Field("deepseek-chat")

    REPORT_ENGINE_API_KEY: Optional[str] = Field(None)
    REPORT_ENGINE_BASE_URL: Optional[str] = Field("https://aihubmix.com/v1")
    REPORT_ENGINE_MODEL_NAME: str = Field("gemini-2.5-pro")

    FORUM_HOST_API_KEY: Optional[str] = Field(None)
    FORUM_HOST_BASE_URL: Optional[str] = Field(None)
    FORUM_HOST_MODEL_NAME: str = Field("qwen-plus")

    KEYWORD_OPTIMIZER_API_KEY: Optional[str] = Field(None)
    KEYWORD_OPTIMIZER_BASE_URL: Optional[str] = Field(None)
    KEYWORD_OPTIMIZER_MODEL_NAME: str = Field("qwen-plus")

    TAVILY_API_KEY: Optional[str] = Field(None)
    ANSPIRE_API_KEY: Optional[str] = Field(None)
    ANSPIRE_BASE_URL: str = Field("https://plugin.anspire.cn/api/ntsearch/search")
    BOCHA_WEB_SEARCH_API_KEY: Optional[str] = Field(None)
    BOCHA_BASE_URL: str = Field("https://api.bocha.cn/v1/ai-search")
    SEARCH_TOOL_TYPE: str = Field("AnspireAPI")


settings = Settings()
