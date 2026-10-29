from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_mode: Literal['demo', 'real'] = 'demo'
    app_timezone: str = 'America/Lima'
    database_url: str = 'sqlite:///data/app.db'
    openai_api_key: str = ''
    openai_vision_model: str = ''
    openai_review_model: str = ''
    deepseek_api_key: str = ''
    deepseek_model: str = ''
    max_tool_rounds: int = Field(6, ge=1, le=10)
    max_parallel_tools: int = Field(3, ge=1, le=5)
    max_output_tokens: int = Field(1800, ge=200, le=4000)
    max_analysis_seconds: int = Field(120, ge=5, le=300)
    max_image_bytes: int = Field(10485760,ge=1024,le=10485760)
    model_xi: float = Field(0.0018,ge=0,le=1)
    price_date: str = ''
    input_price: float | None = None
    output_price: float | None = None


settings = Settings()
