from datetime import datetime, timezone
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


def now():
    return datetime.now(timezone.utc)


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Selection(Strict):
    sport: Literal['football', 'nba'] = 'football'
    competition: str | None = Field(None, max_length=100)
    home: str | None = Field(None, max_length=120)
    away: str | None = Field(None, max_length=120)
    starts_at: datetime | None = None
    market_original: str = Field('', max_length=300)
    market: Literal['1x2', 'total', 'moneyline', 'unsupported'] = '1x2'
    period: str = Field('match', max_length=50)
    line: float | None = Field(None, ge=0, le=500)
    side: str | None = Field(None, max_length=120)
    odds: float | None = Field(None, gt=1, le=10000)
    bookmaker: str | None = Field(None, max_length=100)
    original_text: str = Field('', max_length=5000)
    ambiguous_fields: list[str] = Field(default_factory=list, max_length=20)
    event_id: str | None = Field(None, max_length=200)
    observed_at: datetime = Field(default_factory=now)
    complete_market: dict[str, float] | None = None

    @field_validator('odds', mode='before')
    @classmethod
    def decimal(cls, v):
        return v.replace(',', '.') if isinstance(v, str) else v

    @field_validator('starts_at', 'observed_at')
    @classmethod
    def utc(cls, v):
        if v is not None:
            if v.tzinfo is None:
                raise ValueError('Indica zona horaria (UTC o America/Lima -05:00)')
            return v.astimezone(timezone.utc)
        return v


class Extraction(Strict):
    status: Literal['ok', 'needs_review'] = 'needs_review'
    selections: list[Selection] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list)


class AnalysisRequest(Strict):
    selections: list[Selection] = Field(min_length=1, max_length=20)
    reviewed: Literal[True]
    parent_id: str | None = None


class Evidence(Strict):
    status: Literal['ok', 'partial', 'unavailable', 'unsupported', 'needs_review']
    event_id: str | None = None
    as_of: datetime | None = None
    retrieved_at: datetime = Field(default_factory=now)
    source: dict[str, str | None]
    sample: dict[str, Any] | None = None
    data: Any = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    truncated: bool = False


class Event(Strict):
    id: str
    sport: Literal['football', 'nba']
    competition: str
    season: str
    category: str = 'masculino-profesional'
    starts_at: datetime
    home: str
    away: str
    home_id: str
    away_id: str
    home_abbreviation: str | None = None
    away_abbreviation: str | None = None
    provider: str
    reference: str
