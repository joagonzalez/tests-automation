.PHONY: install test lint format check clean run

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

check: lint test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python src/main.py