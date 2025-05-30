.PHONY: install test lint format clean

install:
	poetry install

test:
	poetry run pytest tests/ --cov=src --cov-report=term-missing

lint:
	poetry run ruff check src tests

format:
	poetry run ruff format src tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} + 