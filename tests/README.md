# TradeBot Test Suite

This directory contains the test suite for the TradeBot automated trading system.

## Directory Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── unit/                    # Unit tests for individual components
│   ├── test_strategies.py   # Tests for trading strategies
│   └── test_tax_calculator.py # Tests for tax calculations
├── integration/             # Integration tests
│   └── test_trade_execution.py # Tests for complete trade flow
└── README.md               # This file
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
poetry install --with dev
```

### Run All Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=. --cov-report=html

# Run with verbose output
poetry run pytest -v
```

### Run Specific Test Categories

```bash
# Run only unit tests
poetry run pytest -m unit

# Run only integration tests
poetry run pytest -m integration

# Skip slow tests
poetry run pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Run strategy tests
poetry run pytest tests/unit/test_strategies.py

# Run specific test
poetry run pytest tests/unit/test_strategies.py::TestMomentumStrategy::test_buy_signal_on_uptrend
```

## Test Coverage Goals

- **Overall**: Minimum 80% code coverage
- **Critical Paths**: 100% coverage (trade execution, risk management)
- **Utilities**: 70% coverage minimum

### Check Coverage

```bash
# Generate coverage report
poetry run pytest --cov=. --cov-report=html

# Open report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Writing Tests

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_example():
    # Arrange: Set up test data and dependencies
    strategy = MomentumStrategy()
    data = create_sample_data()
    
    # Act: Execute the code being tested
    result = strategy.generate_signal(data)
    
    # Assert: Verify the outcome
    assert result is not None
```

### Using Fixtures

Fixtures are defined in `conftest.py`:

```python
def test_with_fixture(sample_ohlcv_data):
    """Use the sample_ohlcv_data fixture."""
    assert len(sample_ohlcv_data) == 100
```

### Mocking External Dependencies

Use `unittest.mock` for mocking:

```python
from unittest.mock import Mock, patch

@patch('module.external_api_call')
def test_with_mock(mock_api):
    mock_api.return_value = {"status": "success"}
    # Test code here
```

## Test Data

### Sample Data Fixtures

Available fixtures (see `conftest.py`):

- `sample_ohlcv_data`: 100 rows of sample stock data
- `empty_dataframe`: Empty DataFrame for edge cases
- `insufficient_data`: DataFrame with minimal data
- `trending_upward_data`: Clear upward trend
- `trending_downward_data`: Clear downward trend
- `sideways_data`: Sideways/ranging market
- `test_db_session`: In-memory test database
- `mock_config`: Test configuration
- `sample_stock_symbols`: List of stock symbols
- `mock_ltp_data`: Mock Last Traded Price data

### Creating Custom Test Data

```python
import pandas as pd
from datetime import datetime, timedelta

def create_custom_data():
    dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
    return pd.DataFrame({
        'open': range(1000, 1050),
        'high': range(1010, 1060),
        'low': range(990, 1040),
        'close': range(1000, 1050),
        'volume': [1000000] * 50
    }, index=dates)
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:
- Trading strategies
- Tax calculations
- Utility functions
- Data models

**Characteristics**:
- Fast execution (< 1 second per test)
- No external dependencies
- Use mocks for dependencies

### Integration Tests (`tests/integration/`)

Test component interactions:
- Trade execution flow
- Database operations
- API integrations (mocked)

**Characteristics**:
- Slower execution
- Test multiple components together
- May use real database (in-memory)

## Continuous Integration

Tests are run automatically on:
- Every pull request
- Every push to main branch

CI requirements:
- All tests must pass
- Code coverage must not decrease
- No linting errors

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in poetry shell
poetry shell

# Or run with poetry
poetry run pytest
```

**Database Errors**
```bash
# Use test database fixture
def test_example(test_db_session):
    # test_db_session is in-memory, clean for each test
```

**Slow Tests**
```bash
# Skip slow tests during development
pytest -m "not slow"
```

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   ```python
   def test_momentum_strategy_generates_buy_signal_on_uptrend():
   ```

2. **One Assert Per Test**: Focus each test on a single behavior
   ```python
   def test_trade_price_is_positive():
       assert trade.price > 0
   ```

3. **Use Fixtures**: Don't repeat setup code
   ```python
   @pytest.fixture
   def setup_data():
       return create_test_data()
   ```

4. **Test Edge Cases**: Include tests for boundary conditions
   ```python
   def test_handles_empty_data():
   def test_handles_zero_quantity():
   ```

5. **Mock External Services**: Don't make real API calls in tests
   ```python
   @patch('groww_api.place_order')
   def test_with_mock(mock_order):
   ```

## Contributing Tests

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or increase coverage
4. Add tests to appropriate directory
5. Update this README if needed

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)

## Contact

For test-related questions, open an issue or contact the maintainers.
