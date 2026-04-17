# Implementation Plan - Python DeepMerge

This plan outlines the creation of a Python `deep_merge` library, converting functionality from the Ruby gem while strictly adhering to JSON/YAML compatible types.

## User Review Required

> [!IMPORTANT]
> **Strict Type Checking**: The library will raise a custom `InvalidTypeError` for any types typically not found in JSON/YAML (e.g., sets, tuples, custom objects).
>
> **Supported Types**: `dict`, `list`, `str`, `int`, `float`, `bool`, `NoneType`.

> [!NOTE]
> **Class-Based Interface**: We will implement a `DeepMerge` class that holds configuration options, with a `merge(destination, source)` method.

## Proposed Changes

### Project Structure (Root)

#### [DONE] [pyproject.toml](file:///Users/frefur/Projects/deep-merge/pyproject.toml)
- Standard build system configuration (using `hatchling` as recommended for modern workflows).
- Fully compatible with `uv`.

> [!NOTE]
> We will use `uv` for dependency management and running commands.

#### [DONE] [deep_merge/__init__.py](file:///Users/frefur/Projects/deep-merge/deep_merge/__init__.py)
- Expose the main `DeepMerge` class.

#### [DONE] [deep_merge/core.py](file:///Users/frefur/Projects/deep-merge/deep_merge/core.py)
- **Class `DeepMerge`**:
    - `__init__(self, **options)`: Initialize with merge options.
    - `merge(self, dest, source)`: Main entry point. Validation checks here.
    - `_merge_recursive(self, dest, source)`: Internal recursive logic.
    - `_validate_type(self, value)`: Helper to enforce strict typing.
    - `_parse_path(self, path_str)`: **[NEW]** AST-based parser for Python-style path strings.

#### Configuration Options
    - `preserve_mismatch` (default: False): If True, mismatched types prevent merge (Target preserved).
    - `exclude_paths` (default: []): List of paths to exclude from source. Supports standard Python syntax (e.g., `server.config.port`, `users[0].name`).
    - `overwrite_list` (default: False): Source list completely replaces Target list.
    - `extend_existing_list` (default: False): **Interleave** strategy (Source[0], Target[0], Source[1]...).
    - `sort_merged_list` (default: False): Sort the final resulting list.
    - `merge_dict_list` (default: False): Merge list items by index (if both dicts).
    - `deduplicate_list` (default: False): Remove duplicates from list.
    - `merge_none_value` (default: False): If True, `None` in source overwrites value in target.

#### Computed Type Constraints
To ensure compatibility with JSON/YAML processing:
- **Allowed Types**: `dict`, `list`, `str`, `int`, `float`, `bool`, `None`.
- **Validation**:
    - During recursive merge, any object not matching `isinstance(obj, (dict, list, str, int, float, bool, type(None)))` will raise `InvalidTypeError`.
    - This creates a hard boundary against "weird Python edge cases" like sets, tuples, or custom classes.

#### [DONE] [deep_merge/exceptions.py](file:///Users/frefur/Projects/deep-merge/deep_merge/exceptions.py)
- `DeepMergeError` (base)
- `InvalidTypeError`

### Testing

#### [DONE] [tests/](file:///Users/frefur/Projects/deep-merge/tests/)
- `test_deep_merge.py`: Unit tests covering al options.
- `test_types.py`: Specific tests for strict type validation.
- `test_path_parsing.py`: **[NEW]** Validation for AST path parsing logic.
- `test_fixes.py`: Regression and edge case tests.

## Verification Plan

### Automated Tests
Run `pytest` to verify all scenarios.

```bash
python3 -m pytest tests/
```

### Manual Verification
Create a simple script `examples/deepmerge.py` to demonstrate the class usage for the user.
