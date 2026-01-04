from pathlib import Path

from typer.testing import CliRunner

from macro_platform.config import get_settings
from macro_platform.ui.cli import app

runner = CliRunner()


def test_cli_run(monkeypatch, tmp_path):
    monkeypatch.setenv("MACRO_OUTPUT_DIR", str(tmp_path))
    get_settings.cache_clear()

    csv_path = Path("data/sample_events.csv")
    result = runner.invoke(app, ["run", "--csv-path", str(csv_path), "--log-level", "WARNING"])

    assert result.exit_code == 0
    assert (tmp_path / "event_counts.png").exists()

    get_settings.cache_clear()


def test_cli_show_config():
    get_settings.cache_clear()
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "tickers" in result.output

