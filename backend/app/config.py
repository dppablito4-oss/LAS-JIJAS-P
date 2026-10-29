from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore',env_ignore_empty=True)
    app_mode: Literal['demo', 'real'] = 'demo'
    ai_profile: Literal['sol', 'economy'] = 'sol'
    app_timezone: str = 'America/Lima'
    database_url: str = 'sqlite:///data/app.db'
    openai_api_key: str = ''
    openai_single_model: str = 'gpt-6.1-sol'
    openai_vision_model: str = 'gpt-6-luna'
    openai_review_model: str = ''
    deepseek_api_key: str = ''
    deepseek_model: str = 'deepseek-flash'
    openai_analysis_effort: Literal['low','medium','high','xhigh','max'] = 'medium'
    deepseek_reasoning_effort: Literal['low','high','max'] = 'high'
    max_tool_rounds: int = Field(6, ge=1, le=10)
    max_parallel_tools: int = Field(3, ge=1, le=5)
    max_output_tokens: int = Field(1800, ge=200, le=4000)
    max_analysis_seconds: int = Field(120, ge=5, le=300)
    max_image_bytes: int = Field(10485760,ge=1024,le=10485760)
    model_xi: float = Field(0.0018,ge=0,le=1)
    price_date: str = ''
    price_model: str = ''
    input_price: float | None = None
    output_price: float | None = None

    @property
    def vision_model(self):
        return self.openai_single_model if self.ai_profile=='sol' else self.openai_vision_model

    @property
    def analyst_provider(self):
        return 'openai' if self.ai_profile=='sol' else 'deepseek'

    @property
    def analyst_model(self):
        return self.openai_single_model if self.ai_profile=='sol' else self.deepseek_model

    @property
    def analyst_configured(self):
        key=self.openai_api_key if self.ai_profile=='sol' else self.deepseek_api_key
        return bool(key and self.analyst_model)

    def ai_summary(self):
        return {'profile':self.ai_profile,'vision_provider':'openai','vision_model':self.vision_model,
                'analyst_provider':self.analyst_provider,'analyst_model':self.analyst_model}


settings = Settings()
