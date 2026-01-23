# Contributing to OSQAr

Thank you for your interest in contributing to OSQAr! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contributing Guidelines](#contributing-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Poetry (for dependency management)
- Git

### Quick Start

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/OSQAr.git
   cd OSQAr
   ```

3. Set up the development environment:
   ```bash
   poetry install
   ```

4. Run the Hello World example to verify setup:
   ```bash
   cd examples/hello_world
   poetry run ./build-and-test.sh
   ```

## Development Setup

### Poetry Environment

This project uses Poetry for dependency management. To set up:

```bash
# Install dependencies
poetry install

# Activate the virtual environment
poetry shell

# Or run commands directly
poetry run python --version
```

### Pre-commit Hooks (Optional)

Install pre-commit hooks to automatically run code quality checks:

```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
OSQAr/
├── .github/                    # GitHub configuration
│   ├── workflows/             # CI/CD workflows
│   └── ISSUE_TEMPLATE/        # Issue templates
├── examples/                  # Example implementations
│   └── hello_world/          # Complete working example
│       ├── src/              # Implementation code
│       ├── tests/            # Test suite
│       ├── diagrams/         # PlantUML diagrams
│       ├── *.rst             # Documentation sources
│       └── _build/           # Generated HTML (not committed)
├── conf.py                    # Sphinx configuration
├── pyproject.toml             # Poetry configuration
├── poetry.lock               # Locked dependencies
├── README.md                 # Project overview
├── CONTRIBUTING.md           # This file
├── LICENSE                   # MIT License
└── .gitignore               # Git ignore rules
```

## Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write descriptive commit messages
- Keep functions focused and single-purpose

### Documentation Standards

- All requirements must have unique IDs following the pattern `^[A-Z0-9_]{3,}`
- Use reStructuredText (.rst) for documentation
- Include traceability links between requirements, architecture, and tests
- Update documentation when making functional changes

### Requirement ID Conventions

| Prefix | Purpose | Example |
|--------|---------|---------|
| `REQ_SAFETY_` | Safety goals and requirements | `REQ_SAFETY_001` |
| `REQ_FUNC_` | Functional requirements | `REQ_FUNC_001` |
| `ARCH_` | Architecture specifications | `ARCH_FUNC_001` |
| `TEST_` | Test case definitions | `TEST_CONVERSION_001` |

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
```
feat: add medical device example
fix: correct PlantUML diagram syntax
docs: update traceability guide
test: add integration test for TSIM
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest examples/hello_world/tests/test_tsim.py

# Run with coverage
poetry run pytest --cov=examples/hello_world/src

# Run documentation tests
poetry run pytest --doctest-modules
```

### Test Structure

- Unit tests for individual components
- Integration tests for end-to-end functionality
- Test names should match TEST_* requirement IDs
- Include docstrings linking to requirements

### Test Coverage

Maintain high test coverage, especially for:
- Safety-critical functions
- Requirement implementation
- Error handling paths

## Documentation

### Building Documentation

```bash
# Build HTML documentation
poetry run sphinx-build -b html . _build/html

# Build with auto-reload (development)
poetry run sphinx-autobuild -b html . _build/html
```

### Documentation Standards

- Use Sphinx with sphinx-needs extension
- Include requirement traceability links
- Generate PlantUML diagrams for architecture
- Maintain bidirectional traceability

### Example Documentation Structure

```
Project Documentation/
├── index.rst              # Table of contents
├── 01_requirements.rst    # Safety and functional requirements
├── 02_architecture.rst    # System architecture and diagrams
├── 03_verification.rst    # Test plans and traceability
├── 04_implementation.rst  # Code examples and implementation
└── 05_test_results.rst    # Test results and compliance
```

## Pull Request Process

### Before Submitting

1. **Update Tests**: Ensure all tests pass and coverage is maintained
2. **Update Documentation**: Update docs for any functional changes
3. **Run Quality Checks**:
   ```bash
   # Code formatting
   poetry run black --check .

   # Type checking (if applicable)
   poetry run mypy .

   # Linting
   poetry run flake8 .
   ```

4. **Test Documentation Build**:
   ```bash
   poetry run sphinx-build -b html . _build/html
   ```

### Creating a Pull Request

1. **Branch Naming**: Use descriptive branch names
   ```
   feature/add-medical-example
   fix/plantuml-rendering
   docs/update-contributing-guide
   ```

2. **Pull Request Template**: Fill out the PR template with:
   - Clear description of changes
   - Links to related issues
   - Testing instructions
   - Screenshots/docs for UI changes

3. **Code Review**: Address reviewer feedback promptly

### After Merge

- Delete your feature branch
- Pull latest changes from main
- Update any dependent branches

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Step-by-step instructions
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, Poetry version
- **Logs/Error Messages**: Any relevant output

### Feature Requests

For feature requests, please include:

- **Problem**: What problem are you trying to solve?
- **Solution**: Proposed solution
- **Alternatives**: Alternative approaches considered
- **Use Case**: How would this be used?

### Security Issues

For security-related issues, please email the maintainers directly rather than creating a public issue.

## Recognition

Contributors will be recognized in:
- Repository contributor list
- Release notes
- Project documentation

Thank you for contributing to OSQAr! Your efforts help advance functional safety standards and practices.