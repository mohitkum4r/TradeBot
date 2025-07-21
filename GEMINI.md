# AutoTrade Project Context for Gemini

This project is an automated trading system designed to interact with the Groww API.

## Key Directories and Files:

- `autotrade/`: Core application logic, including database models, services, and strategies.
- `app/`: Application-wide configurations and dependency injection setup.
- `domain/`: Contains domain-specific models and potentially abstract interfaces.
- `infrastructure/`: Implementations for external services like brokers, data providers, ML models, etc.
- `interfaces/`: Defines interfaces for various components to ensure modularity and testability.
- `use_cases/`: Contains high-level application logic, orchestrating interactions between domain and infrastructure layers (e.g., `backtest.py`, `trade_executor.py`).
- `main.py`: The entry point of the application.
- `pyproject.toml`: Project dependencies and metadata (using Poetry).
- `.env`: Environment variables for API keys, database URLs, and configuration.

## Current State and Goals:

The project is currently undergoing a restructuring to improve modularity, maintainability, and error handling. The primary goals are:
- Eliminate duplicate `config.py` files.
- Consolidate all dependencies within `pyproject.toml`.
- Ensure logical placement of files within the project structure.
- Fix all warnings and errors (linting, type checking, runtime).
- Ensure the application works correctly and is modular.
- Integrate Groww API documentation for better understanding of API interactions.

## Groww API Documentation:

The Groww API documentation is located at `/Users/mohkumar32/Downloads/Groww`. This documentation should be consulted for accurate API usage, rate limits, and data formats when implementing or modifying interactions with Groww.

## Next Steps:

I will continue by:
1. Reviewing `pyproject.toml` and `requirements.txt` to consolidate dependencies.
2. Analyzing `main.py` and other core files for logical correctness and adherence to the new structure.
3. Implementing necessary fixes for any identified issues.
4. Ensuring all components are modular and follow good software engineering practices.
