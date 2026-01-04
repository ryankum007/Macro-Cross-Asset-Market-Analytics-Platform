"""Entrypoint for running the CLI via `python -m macro_platform.app`."""

from macro_platform.ui.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()

