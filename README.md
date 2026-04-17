# DeepMerge

A Python library for deep merging dictionaries, inspired by the Ruby `deep_merge` gem.
Strictly adheres to JSON/YAML compatible types (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`).

## Features

- **Deep Merging**: Recursively merges nested dictionaries and lists.
- **Strict Typing**: Validates inputs are JSON/YAML compatible; raises `InvalidTypeError` otherwise.
- **Configurable Strategies**:
    - **Overwrite** vs **Interleave** list merging.
    - **Exclude Paths** to ignore specific keys.
    - **Type Mismatch** handling.

## Installation

```bash
pip install deep-merge
```

## Usage

```python
from deep_merge import DeepMerge

source = {"server": {"port": 8080}}
target = {"server": {"host": "localhost"}}

# Default Merge
merger = DeepMerge()
result = merger.merge(target, source)
# {'server': {'host': 'localhost', 'port': 8080}}
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `exclude_paths` | `[]` | List of paths to ignore (e.g. `["x.y"]`, `["users[0].name"]`). Supports dot and bracket notation. |
| `extend_existing_list` | `False` | Interleave source/target lists (`[S0, T0, S1...]`). Default is overwrite by index. |
| `overwrite_list` | `False` | If True, source list completely replaces target list. |
| `preserve_mismatch` | `False` | If True, keep target value on type mismatch. |
| `merge_none_value` | `False` | If True, `None` in source overwrites value in target. |
| `deduplicate_list` | `False` | Remove duplicate items from the merged list. Preserves order if possible. |
| `sort_merged_list` | `False` | Sort the resulting merged list. |

