#!/bin/bash
# run_checks.sh

echo "Running mypy for static type checking..."
poetry run mypy .

echo -e "\nRunning ruff for linting and formatting checks..."
poetry run ruff check .
poetry run ruff format --check .

echo -e "\nRunning black for formatting checks..."
poetry run black --check .

echo -e "\nAll checks passed!"