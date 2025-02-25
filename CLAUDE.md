# Wardley Package Demo - Developer Guidelines

## Commands
- Run application: `streamlit run streamlit_app.py`
- Install dependencies: `pip install -r requirements.txt`
- Format code: `black .`
- Type check: `mypy .`
- Lint: `flake8 .` or `pylint .`

## Code Style Guidelines
- **Imports**: Group imports: stdlib, third-party, local - sorted alphabetically within groups
- **Formatting**: Follow PEP 8 guidelines with 88-character line limit (Black compatible)
- **Type Hints**: Use typing annotations for all function parameters and return types
- **Docstrings**: Google style docstrings for all functions and classes
- **Error Handling**: Use specific exception types and document with appropriate error messages
- **Naming Conventions**:
  - snake_case for variables and functions
  - CamelCase for classes
  - UPPER_CASE for constants
- **File Organization**: Group related functions together, constants at the top
- **Dependencies**: Keep requirements.txt updated with minimal necessary packages