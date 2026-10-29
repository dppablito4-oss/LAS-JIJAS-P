from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', allow_inf_nan=False, env_ignore_empty=True)
    app_mode: Literal['demo', 'real'] = 'demo'
    ai_profile: Literal['sol','economy','hybrid'] = 'sol'
    openai_single_model: str = 'gpt-6.1-sol'
    openai_analysis_effort: Literal['low','medium','high','xhigh','max'] = 'medium'
    openai_analysis_mode: Literal['standard','pro'] = 'standard'
    app_timezone: str = 'America/Lima'
    database_url: str = 'sqlite:///data/app.db'
    openai_api_key: str = ''
    openai_vision_model: str = 'gpt-6-luna'
    openai_review_model: str = 'gpt-6.1-sol'
    openai_review_enabled: bool = True
    openai_vision_effort: Literal['none','low','medium','high','xhigh','max'] = 'low'
    openai_review_effort: Literal['low','medium','high','xhigh','max'] = 'high'
    openai_review_mode: Literal['standard','pro'] = 'standard'
    deepseek_api_key: str = ''
    deepseek_model: str = 'deepseek-flash'
    deepseek_thinking: bool = True
    deepseek_reasoning_effort: Literal['low','high','max'] = 'high'
    max_tool_rounds: int = Field(6, ge=1, le=10)
    max_parallel_tools: int = Field(3, ge=1, le=5)
    max_output_tokens: int = Field(8192, ge=256, le=32768)
    max_analysis_seconds: int = Field(240, ge=5, le=600)
    model_timeout_seconds: int = Field(45, ge=1, le=120)
    ai_timeout_seconds: int = Field(90, ge=1, le=180)
    vision_max_tokens: int = Field(4096, ge=256, le=32768)
    review_max_tokens: int = Field(8192, ge=256, le=32768)
    deepseek_max_tokens: int = Field(8192, ge=256, le=32768)
    max_history_age_days: int = Field(30, ge=1, le=365)
    max_quote_age_hours: int = Field(24, ge=1, le=168)
    max_image_bytes: int = Field(10485760,ge=1024,le=10485760)
    model_xi: float = Field(0.0018,ge=0,le=1)
    price_date: str = ''
    price_model: str = ''
    input_price: float | None = Field(None, ge=0)
    output_price: float | None = Field(None, ge=0)

    @field_validator('input_price','output_price',mode='before')
    @classmethod
    def optional_price(cls,value):
        return None if isinstance(value,str) and not value.strip() else value


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
                'analyst_provider':self.analyst_provider,'analyst_model':self.analyst_model,
                'review_model':self.openai_review_model if self.ai_profile=='hybrid' and self.openai_review_enabled else None}

settings = Settings()
