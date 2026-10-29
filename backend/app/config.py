from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore',env_ignore_empty=True,allow_inf_nan=False)
    app_mode: Literal['demo', 'real'] = 'demo'
    ai_profile: Literal['sol', 'economy', 'hybrid'] = 'sol'
    app_timezone: str = 'America/Lima'
    database_url: str = 'sqlite:///data/app.db'
    openai_api_key: str = ''
    openai_single_model: str = 'gpt-6.1-sol'
    openai_vision_model: str = 'gpt-6-luna'
    openai_vision_effort: Literal['low','medium','high','xhigh','max'] = 'low'
    openai_review_model: str = 'gpt-6.1-sol'
    openai_review_enabled: bool = False
    openai_review_effort: Literal['low','medium','high','xhigh','max'] = 'high'
    openai_review_mode: Literal['standard','pro'] = 'standard'
    deepseek_api_key: str = ''
    deepseek_model: str = 'deepseek-flash'
    openai_analysis_effort: Literal['low','medium','high','xhigh','max'] = 'medium'
    openai_analysis_mode: Literal['standard','pro'] = 'standard'
    deepseek_reasoning_effort: Literal['low','high','max'] = 'high'
    deepseek_thinking: bool = True
    max_tool_rounds: int = Field(6, ge=1, le=10)
    max_parallel_tools: int = Field(3, ge=1, le=5)
    max_output_tokens: int = Field(1800, ge=200, le=32768)
    vision_max_tokens: int | None = Field(None,ge=200,le=32768)
    review_max_tokens: int | None = Field(None,ge=200,le=32768)
    deepseek_max_tokens: int | None = Field(None,ge=200,le=32768)
    max_analysis_seconds: int = Field(120, ge=5, le=300)
    model_timeout_seconds: int = Field(45,ge=1,le=180)
    ai_timeout_seconds: int = Field(90,ge=1,le=300)
    max_history_age_days: int = Field(30,ge=1,le=3650)
    max_quote_age_hours: float = Field(24,gt=0,le=8760)
    odds_provider: Literal['manual'] = 'manual'
    max_image_bytes: int = Field(10485760,ge=1024,le=10485760)
    model_xi: float = Field(0.0018,ge=0,le=1)
    price_date: str = ''
    price_model: str = ''
    input_price: float | None = Field(None,ge=0)
    output_price: float | None = Field(None,ge=0)

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

    @property
    def review_enabled(self):
        return self.openai_review_enabled

    @property
    def review_effort(self):
        return self.openai_review_effort

    def token_limit(self,stage):
        limits={'vision':self.vision_max_tokens,'review':self.review_max_tokens,'deepseek':self.deepseek_max_tokens}
        return limits.get(stage) or self.max_output_tokens

    def ai_summary(self):
        return {'profile':self.ai_profile,'vision_provider':'openai','vision_model':self.vision_model,
                'analyst_provider':self.analyst_provider,'analyst_model':self.analyst_model,
                'review_enabled':self.review_enabled,'review_model':self.openai_review_model if self.review_enabled else None,
                'review_mode':self.openai_review_mode if self.review_enabled else None,
                'review_effort':self.review_effort if self.review_enabled else None}


settings = Settings()
