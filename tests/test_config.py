from macro_platform.config import Settings, get_settings


def test_default_settings_populated():
    settings = get_settings()
    assert settings.market.tickers
    assert settings.date_range.start_date
    assert settings.data_dir.name == "data"


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("MACRO_ENV", "production")
    # new instance to pick env var
    settings = Settings()
    assert settings.env == "production"

