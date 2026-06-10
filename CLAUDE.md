# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A student grade management CLI app, refactored from the original single-file `task.py` into a multi-module architecture with separated concerns, comprehensive error handling, detailed docstrings, and full unit test coverage.

## How to Run

```bash
python main.py          # Run the application
```

## How to Test

```bash
python -m unittest discover tests -v   # Run all 124 tests
```

No dependencies beyond Python 3 stdlib. No virtual environment or package installation needed.

The original (unrefactored) version is preserved at `task.py` for comparison.

## Architecture

```
main.py                         # App class: entry point, uniform dispatch (all handlers share signature)
student_system/
  __init__.py
  exceptions.py                 # Custom exception hierarchy (StudentSystemError base)
  models.py                     # Student dataclass, MenuAction enum, validate_score/validate_name
  manager.py                    # StudentManager — pure business logic, raises on errors
  storage.py                    # Storage — atomic JSON file persistence (temp file + os.replace)
  ui.py                         # All print/input, reusable validators, KeyboardInterrupt handling
tests/
  test_exceptions.py            # Exception hierarchy tests
  test_models.py                # Student, MenuAction, validation tests
  test_manager.py               # StudentManager CRUD/stats/ranking tests
  test_storage.py               # Storage save/load/atomic write/error tests
  test_integration.py           # Cross-module workflow tests
```

### Key design decisions

- **Exception-driven error handling**: `manager.py` methods raise `StudentNotFoundError`, `ValidationError`, etc. rather than returning `False` or `None`. A unified `StudentSystemError` base class allows catch-all error handling in `main.py`.
- **`App` class** (`main.py`): All handler methods share the same `(self) -> None` signature via closure over `self.manager` and `self.storage`, eliminating the old signature-mismatch hack. Dictionary dispatch with no special cases.
- **Atomic writes** (`storage.py`): Data is written to a temp file then `os.replace`'d atomically — a crash during save won't corrupt existing data.
- **Input robustness** (`ui.py`): `KeyboardInterrupt` and `EOFError` are handled in every input function for graceful shutdown.
- **`Student`** dataclass validates in `__post_init__` — ensures data integrity at creation time.
- **Data flow**: `main.py` → `ui.py` (get input) → `manager.py` (mutate state) → `ui.py` (display result). For persistence: `main.py` → `manager.to_dict()` → `storage.save()`.
