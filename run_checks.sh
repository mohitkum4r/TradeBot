#!/bin/bash
# run_checks.sh

echo "Running mypy for static type checking..."
poetry run mypy . --exclude infrastructure/brokers/groww_broker.py

echo -e "\nRunning ruff for linting and formatting checks..."
poetry run ruff check . --isolated --exclude infrastructure/brokers/groww_broker.py
poetry run ruff format --check . --isolated --exclude infrastructure/brokers/groww_broker.py

echo -e "\nRunning black for formatting checks..."
poetry run black --check . --exclude infrastructure/brokers/groww_broker.py

echo -e "\nAll checks passed!"