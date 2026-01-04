from pathlib import Path

from typer.testing import CliRunner

from macro_platform.config import get_settings
from macro_platform.ui.cli import app

runner = CliRunner()


def test_cli_run(monkeypatch, tmp_path):
    monkeypatch.setenv("MACRO_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()

    csv_path = tmp_path / "sample_events.csv"
    csv_path.write_text(
        "date,ticker,event,impact\n"
        "2024-01-15,SPY,Fed speech,medium\n"
        "2024-02-01,TLT,CPI release,high\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["run", "--csv-path", str(csv_path), "--log-level", "WARNING"])

    assert result.exit_code == 0
    assert (tmp_path / "event_counts.png").exists()

    get_settings.cache_clear()


def test_cli_show_config():
    get_settings.cache_clear()
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "tickers" in result.output
