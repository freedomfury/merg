# DeepMerge Python Implementation Walkthrough

I have successfully converted the `deep_merge` Ruby logic to a robust Python package, strictly adhering to JSON/YAML types and implementing the requested list strategies (Interleave/Overwrite).

## Key Features Implemented

### 1. Strict Type Validation
The library enforces **JSON/YAML compatible types** (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`). Use of sets, tuples, or custom objects raises `InvalidTypeError`.

```python
from deep_merge import DeepMerge, InvalidTypeError

merger = DeepMerge()
try:
    merger.merge({"a": 1}, {"a": (1, 2)}) # Tuple is invalid
except InvalidTypeError as e:
    print(e) # "source[a] has invalid type: <class 'tuple'>"
```

### 2. List Strategies
Two primary strategies for list merging, matching your specifications:

*   **Overwrite by Index (Default)**: Source items overwrite target items at the same index. Extra target items are preserved.
*   **Interleave (`extend_existing_list=True`)**: Interleaves Source and Target items at the same index (`S[0], T[0], S[1], T[1]...`).

### 3. Exclusion
A modern `exclude_paths` option supports both legacy dot-notation and **standard Python syntax**. We use Python's built-in `ast` module to safely parse paths, avoiding the need for heavy dependencies like Jinja2.

```python
merger = DeepMerge(exclude_paths=[
    "server.password",          # Dot notation
    "users[0].password",        # Bracket notation (List index)
    "config['secret_key']"      # Bracket notation (Dict key)
])
result = merger.merge(dest, source)
```

## Verification

### Automated Tests
Run the comprehensive test suite (26 cases + strict type checks):

```bash
uv run pytest
```

### Manual Verification
An example script is available at `examples/deepmerge.py`.

```bash
uv run python examples/deepmerge.py
```

Output:
```yaml
--- Example 1: Default Merge (Overwrite/Index) ---
tags:
- dev   # Overwrote 'base'
- http  # Appended from target

--- Example 2: Extend List (Interleave) ---
tags:
- dev   # Source[0]
- base  # Target[0]
- http  # Target[1]
```
