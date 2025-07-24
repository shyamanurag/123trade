# Code Analysis Scripts

This directory contains various scripts for analyzing and improving code quality.

## Available Scripts

### 1. `code_analysis.py`
**Purpose**: Comprehensive code quality analysis
- Runs multiple tools: pylint, mypy, bandit, flake8, black
- Generates detailed reports in `code_analysis_reports/` directory
- Creates a summary report of all tools

**Usage**:
```bash
python scripts/code_analysis.py
```

### 2. `quick_analysis.py`
**Purpose**: Quick code quality check with essential tools
- Runs only flake8, mypy, and bandit
- Shows results directly in console
- Faster than full analysis

**Usage**:
```bash
python scripts/quick_analysis.py
```

### 3. `focused_analysis.py`
**Purpose**: Analyzes only main Python files, excluding tests
- Focuses on core application files
- Excludes test files and generated code
- More targeted results

**Usage**:
```bash
python scripts/focused_analysis.py
```

### 4. `auto_fix_style.py`
**Purpose**: Automatically fixes common style issues
- Fixes whitespace and formatting with autopep8
- Sorts imports with isort
- Applies consistent formatting with black

**Usage**:
```bash
python scripts/auto_fix_style.py
```

## Installation

Install required tools:
```bash
pip install flake8 mypy bandit pylint black isort autopep8
```

Or use the test requirements:
```bash
pip install -r requirements-test.txt
```

## Common Issues and Solutions

### Unused Imports (F401)
- Remove imports that aren't used in the file
- Or use `# noqa: F401` if the import is needed for re-export

### Line Too Long (E501)
- Break long lines at appropriate points
- Or configure max line length in your tools

### Whitespace Issues (W293, W291)
- Run `auto_fix_style.py` to fix automatically
- Or use your editor's "trim trailing whitespace" feature

### Security Issues (Bandit)
- Review each security warning carefully
- Add `# nosec` comment if you've verified the code is safe
- Never ignore security warnings without understanding them

## Best Practices

1. Run `quick_analysis.py` before committing code
2. Run `code_analysis.py` before major releases
3. Use `auto_fix_style.py` to maintain consistent formatting
4. Address security issues (bandit) immediately
5. Keep type hints up to date for better mypy results 