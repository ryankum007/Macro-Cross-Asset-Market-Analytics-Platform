"""Command-line entrypoints for the macro platform."""

from __future__ import annotations

from pathlib import Path

import typer

from macro_platform.analytics.basic_metrics import summarize_events
from macro_platform.config import Settings, get_settings
from macro_platform.ingest.csv_loader import load_event_data
from macro_platform.logging_utils import setup_logging
from macro_platform.viz.plotting import plot_event_counts

app = typer.Typer(help="Macro cross-asset analytics pipeline")

CSV_PATH_OPTION = typer.Option(
    None,
    help="Path to event CSV. Defaults to bundled sample_events.csv.",
)
LOG_LEVEL_OPTION = typer.Option(
    None,
    help="Override log level (DEBUG, INFO, WARNING...).",
)


@app.command()
def run(
    csv_path: Path | None = CSV_PATH_OPTION,
    log_level: str | None = LOG_LEVEL_OPTION,
) -> None:
    """Run the ingest -> analytics -> visualization flow."""

    settings: Settings = get_settings()
    level = log_level or settings.logging_level
    logger = setup_logging(level)

    selected_csv = csv_path or settings.data_dir / "sample_events.csv"
    events = load_event_data(selected_csv)

    summary = summarize_events(events)
    plot_path = plot_event_counts(summary.get("by_ticker", {}), settings.output_dir)

    logger.info("Run completed: %s", summary)
    typer.echo(f"Total events: {summary['total']}")
    typer.echo(f"Plot saved to: {plot_path}")


@app.command(name="config")
def show_config() -> None:
    """Display the active settings."""

    settings = get_settings()
    typer.echo(settings.model_dump_json(indent=2, exclude_none=True))


if __name__ == "__main__":
    app()
