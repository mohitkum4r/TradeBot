# Contributing to TradeBot

Thank you for considering contributing to TradeBot! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow Python community standards

## Getting Started

### Prerequisites

1. Python 3.12+
2. Poetry for dependency management
3. Git for version control
4. Understanding of trading concepts (helpful but not required)

### Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/TradeBot.git
cd TradeBot

# Install dependencies
poetry install --no-root

# Install development dependencies
poetry install --with dev

# Activate virtual environment
poetry shell
```

## Development Workflow

### 1. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style
- Add type hints to all functions
- Write docstrings for public APIs

### 3. Run Quality Checks

```bash
# Run all checks
bash run_checks.sh

# Or individually:
poetry run mypy .
poetry run ruff check .
poetry run black --check .
```

### 4. Write Tests

```bash
# Run tests (when test suite is implemented)
poetry run pytest

# With coverage
poetry run pytest --cov=. --cov-report=html
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"

# Follow conventional commits:
# feat: new feature
# fix: bug fix
# docs: documentation changes
# refactor: code refactoring
# test: adding tests
# chore: maintenance tasks
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use Black for formatting (line length: 88)
- Use Ruff for linting
- Add type hints (mypy compatible)

### Example

```python
from typing import Optional
import pandas as pd


def calculate_indicator(
    data: pd.DataFrame,
    period: int = 14,
    multiplier: float = 2.0
) -> Optional[pd.Series]:
    """
    Calculate a technical indicator.
    
    Args:
        data: OHLCV DataFrame with 'close' column
        period: Lookback period for calculation
        multiplier: Multiplier for the indicator
    
    Returns:
        Series with indicator values, or None if insufficient data
        
    Raises:
        ValueError: If period is less than 1
        
    Example:
        >>> df = pd.DataFrame({'close': [100, 101, 102]})
        >>> result = calculate_indicator(df, period=2)
    """
    if period < 1:
        raise ValueError("Period must be at least 1")
    
    if len(data) < period:
        return None
    
    # Implementation here
    return data['close'].rolling(window=period).mean() * multiplier
```

## Adding New Features

### Adding a Trading Strategy

1. Create new file in `domain/strategies/`
2. Inherit from `BaseStrategy`
3. Implement `generate_signal()` method
4. Add docstrings and type hints
5. Register in `StrategySelector` if needed

Example:

```python
# domain/strategies/my_strategy.py
from typing import Tuple
import pandas as pd
from .base_strategy import BaseStrategy


class MyStrategy(BaseStrategy):
    """
    Brief description of your strategy.
    
    This strategy implements [describe approach].
    
    Parameters:
        param1: Description
        param2: Description
    """
    
    def __init__(self, param1: int = 14):
        self.param1 = param1
    
    def generate_signal(
        self,
        data: pd.DataFrame,
        **kwargs
    ) -> Tuple[str, str, str]:
        """
        Generate trading signal.
        
        Args:
            data: OHLCV DataFrame
            **kwargs: Additional context
        
        Returns:
            Tuple of (stock, action, reason)
            action: 'BUY', 'SELL', or 'HOLD'
        """
        # Implementation
        return ("STOCK", "BUY", "Reason for signal")
```

### Adding Tests

Create test files in `tests/` directory:

```python
# tests/unit/test_my_strategy.py
import pytest
import pandas as pd
from domain.strategies.my_strategy import MyStrategy


@pytest.fixture
def sample_data():
    """Provide sample OHLCV data."""
    return pd.DataFrame({
        'open': [100, 101, 102],
        'high': [105, 106, 107],
        'low': [95, 96, 97],
        'close': [100, 101, 102],
        'volume': [1000, 1100, 1200]
    })


def test_strategy_generates_signal(sample_data):
    """Test strategy generates valid signal."""
    strategy = MyStrategy()
    stock, action, reason = strategy.generate_signal(sample_data)
    
    assert action in ['BUY', 'SELL', 'HOLD']
    assert isinstance(reason, str)
    assert len(reason) > 0
```

## Pull Request Guidelines

### PR Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Commits are meaningful and follow conventions
- [ ] PR description explains changes clearly

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No warnings in linting
```

## Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: Maintainer reviews the code
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, PR will be merged

## Areas for Contribution

### High Priority
- [ ] Comprehensive test suite
- [ ] CI/CD pipeline setup
- [ ] Enhanced error handling
- [ ] Performance optimizations
- [ ] Docker containerization

### Medium Priority
- [ ] Additional trading strategies
- [ ] Advanced risk management
- [ ] Monitoring and alerting
- [ ] API documentation
- [ ] User interface/dashboard

### Low Priority
- [ ] Code examples and tutorials
- [ ] Strategy backtesting reports
- [ ] Performance benchmarking
- [ ] Multi-broker support

## Questions or Problems?

- **Open an Issue**: For bugs or feature requests
- **Discussions**: For questions and ideas
- **Email**: mo.kum4r@gmail.com

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in relevant documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to TradeBot! 🎉
