"""Application configuration using Pydantic settings."""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketUniverse(BaseModel):
    """Tickers and macro series covered by the platform."""

    tickers: list[str] = Field(default_factory=lambda: ["SPY", "TLT", "GLD"])
    fred_series_ids: list[str] = Field(
        default_factory=lambda: ["DGS10", "T10Y2Y", "CPALTT01USM657N"]
    )


class DateRange(BaseModel):
    """Default analysis window."""

    start_date: date = date(2020, 1, 1)
    end_date: date = Field(default_factory=date.today)


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_prefix="MACRO_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    env: Literal["development", "production", "test"] = "development"
    data_dir: Path = Path("data")
    output_dir: Path = Path("outputs")
    logging_level: str = "INFO"
    market: MarketUniverse = MarketUniverse()
    date_range: DateRange = DateRange()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings
