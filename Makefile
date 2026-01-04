.PHONY: install lint format typecheck test run clean

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

test:
	uv run pytest

run:
	uv run python -m macro_platform.app run

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
