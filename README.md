# merg

Pythonic deep merging of dicts and lists, built specifically for configuration data — YAML and JSON — with strict type validation.

## Why merg?

Most Python deep merge libraries are designed for general-purpose data structures. `merg` is scoped specifically to configuration data — the types that actually appear in YAML and JSON files (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`). Anything else is rejected at merge time. Inputs are never mutated.

## Installation

```bash
pip install merg
```

## Development

```bash
git clone https://github.com/freedomfury/merg
cd merg
make venv       # install dev dependencies
make            # lint + tests (default)
```

| Command | What it does |
|---|---|
| `make` | lint + full test suite (default) |
| `make lint` | ruff check only |
| `make tests` | pytest only |
| `make build` | build `dist/` artifacts locally |
| `make deploy` | push `v{version}` tag → PyPI |
| `make clean` | remove `dist/`, caches |

`make deploy` runs the full test suite first and aborts if there are uncommitted changes. TestPyPI publishing is manual — use the **Run workflow** button in the GitHub Actions tab when needed.

## Quick Start

```python
from merg import DeepMerge

defaults = {
    "server": {"host": "localhost", "port": 80},
    "logging": {"level": "INFO", "file": "/var/log/app.log"},
}

overrides = {
    "server": {"port": 8080},
    "logging": {"level": "DEBUG"},
}

merg = DeepMerge()
result = merg.merge(defaults, overrides)
# {
#     "server": {"host": "localhost", "port": 8080},
#     "logging": {"level": "DEBUG", "file": "/var/log/app.log"},
# }
```

## Type Scope

`merg` is strict about types by design. Only the common subset of JSON and YAML data is accepted:

| Type | Supported |
|------|-----------|
| `dict` | Yes |
| `list` | Yes |
| `str` | Yes |
| `int` | Yes |
| `float` | Yes |
| `bool` | Yes |
| `None` | Yes |
| `set`, `tuple`, `frozenset` | No — raises `InvalidTypeError` |
| `datetime`, `date` | No — raises `InvalidTypeError` |
| Custom classes | No — raises `InvalidTypeError` |

This narrowness is intentional. If your data contains unsupported types, convert them before merging.

**Watch out for YAML dates.** YAML implicitly resolves unquoted date-like scalars to `date`/`datetime` objects — which merg rejects. This commonly bites Ansible users and anyone loading YAML with `yaml.safe_load`. Quote the value to keep it a string:

```yaml
deploy_date: "2026-08-18"   # str  — merges fine (single quotes work too)
deploy_date: 2026-08-18     # date — raises InvalidTypeError
```

## Options

Instantiate `DeepMerge` with keyword arguments to control merge behavior. The instance is stateless after construction — create one and call `merge()` as many times as you like.

### `preserve_mismatch` (default: `False`)

When source and target values have different types at the same key, controls which value wins.

```python
merg = DeepMerge(preserve_mismatch=True)
merg.merge({"a": 1}, {"a": "two"})
# {"a": 1}  — target kept because types differ

merg = DeepMerge(preserve_mismatch=False)  # default
merg.merge({"a": 1}, {"a": "two"})
# {"a": "two"}  — source wins
```

A `None` target is treated as absent, not as a protected value — YAML turns a blank key or a stubbed section into `None`, and a patch supplying the real value fills it regardless of `preserve_mismatch`.

### `exclude_paths` (default: `[]`)

Remove specific paths from the **patch** before merging — whatever remains merges by the ordinary rules. Supports dot notation, bracket notation, and raw tuples.

```python
merg = DeepMerge(exclude_paths=["server.port", "db['password']"])
merg.merge(
    {"server": {"port": 80, "host": "old"}, "db": {"password": "secret"}},
    {"server": {"port": 9999, "host": "new"}, "db": {"password": "hacked"}},
)
# {"server": {"port": 80, "host": "new"}, "db": {"password": "secret"}}
```

Excluded paths are matched against the patch's own structure: a dropped value is never inspected (a scalar, a list, `None`, or a knockout marker all behave the same), and a path absent from the patch is a no-op. There is no target-side behavior — the base is never protected, pinned, or inspected.

Prefer excluding **keys**. A path ending in a bare list index addresses a position, and dropping an element shifts the elements after it one slot earlier, changing what the rest of the patch lines up with. Note also that a key can be removed by a patch two ways — `{'a': '--'}` or `{'--a': ''}` — so blocking both spellings means excluding both `a` and `--a`.

### `overwrite_list` (default: `False`)

When `True`, source list completely replaces target list instead of merging by index.

```python
merg = DeepMerge(overwrite_list=True)
merg.merge({"tags": ["a", "b", "c"]}, {"tags": ["x"]})
# {"tags": ["x"]}
```

Mutually exclusive with `extend_existing_list` — setting both raises `TypeError`.

### `extend_existing_list` (default: `False`)

Interleave source and target list items instead of overwriting by index.

```python
merg = DeepMerge(extend_existing_list=True)
merg.merge({"x": ["T1", "T2"]}, {"x": ["S1", "S2"]})
# {"x": ["S1", "T1", "S2", "T2"]}
```

Mutually exclusive with `overwrite_list` — the two name different list-assembly
strategies, so setting both raises `TypeError` rather than silently picking one.

### `deduplicate_list` (default: `False`)

Remove duplicate items from merged lists. Order is preserved.

```python
merg = DeepMerge(extend_existing_list=True, deduplicate_list=True)
merg.merge({"x": ["a", "b"]}, {"x": ["b", "c"]})
# {"x": ["b", "a", "c"]}
```

### `sort_merged_list` (default: `False`)

Sort list items after merging. Silently skipped if items are not comparable.

```python
merg = DeepMerge(extend_existing_list=True, sort_merged_list=True)
merg.merge({"x": [3, 1]}, {"x": [5, 2]})
# {"x": [1, 2, 3, 5]}
```

### `knockout_prefix` (default: `""`)

Set `knockout_prefix` to a marker string (e.g. `"--"`) to enable removal semantics. There is exactly one removal form — the prefix plus a name — and it addresses two positions:

- **On a dict key**, `--a` removes key `a` from the target.
- **As a list item**, `--x` removes target items whose **value** equals `x`, wherever they sit. Removal addresses values, not positions — `--0` does not remove a list's first element.

Everything else is data, including a bare prefix: `{"a": "--"}` assigns the two-character string `"--"`, and `["--"]` merges as an ordinary list item.

```python
merg = DeepMerge(knockout_prefix="--")
merg.merge({"a": 1, "b": 2}, {"--a": ""})
# {"b": 2}

merg = DeepMerge(knockout_prefix="--")
merg.merge(["one", "two", "three"], ["--one", "four"])
# ["two", "three", "four"]
```

**On dict keys** — the *value* under a knockout key is irrelevant and discarded — it exists only because dict entries need one; use `""`, `None`, or anything else.

```python
merg = DeepMerge(knockout_prefix="--")
merg.merge({"a": 1, "b": 2}, {"--a": None})
# {"b": 2}

# The value doesn't matter — these are all equivalent:
merg.merge({"a": 1}, {"--a": None})       # {}
merg.merge({"a": 1}, {"--a": "ignored"})  # {}
merg.merge({"a": 1}, {"--a": [1, 2, 3]})  # {}
```

Knocking out a missing key is a no-op. If a source dict contains both `"--a"` and `"a"`, the knockout runs first — wiping any existing value in the target — and then `"a"` is inserted as a fresh key. It is *not* merged with the original target value, so this is the way to replace a nested dict outright instead of deep-merging into it:

```python
merg = DeepMerge(knockout_prefix="--")
merg.merge({"a": {"x": 1}}, {"--a": None, "a": {"y": 2}})
# {"a": {"y": 2}}    ← "x": 1 is gone; no deep merge happened
```

In YAML, this is typically written with a null value (any of these forms work — they all parse to `None`):

```yaml
'--key_to_remove':         # empty → null
'--another_key': null
'--third_key': ~
```

**Limitations of a string-prefix scheme** — know them before enabling:

- Removal matches **string** values only. `["--443"]` cannot remove the integer `443`, and a list of dicts (`users:`, `volumes:`, `rules:`) has no removal form at all.
- **In-band collision:** data whose string starts with the prefix is read as an instruction. `args: ["--quiet"]` in a patch removes an item named `quiet` rather than adding a flag. The prefix is configurable precisely so you can avoid this — pick something your data never starts with.
- In YAML, avoid `&`, `*`, `!`, `#`, `~`, and `@` as prefixes — they're the anchor, alias, tag, comment, null, and reserved indicators.

### `merge_none_value` (default: `False`)

When `True`, a `None` in source overwrites the target value. By default, `None` values in source are ignored and the target value is preserved.

```python
merg = DeepMerge(merge_none_value=True)
merg.merge({"a": "keep"}, {"a": None})
# {"a": None}

merg = DeepMerge()  # default
merg.merge({"a": "keep"}, {"a": None})
# {"a": "keep"}
```

## Why merg vs other libraries?

| | **merg** | **deepmerge** | **mergedeep** |
|---|---|---|---|
| Type safety | Strict — rejects `set`, `tuple`, `datetime`, etc. | Permissive — merges anything | Permissive |
| API style | Options dict | Strategy classes | Function call |
| Ruby `deep_merge` semantics | Yes — inspired by the gem | No | No |
| Knockout prefix support | Yes | No | No |
| Input mutation | Never — `deepcopy` throughout | Mutates target by default | Mutates target by default |
| Scope | Config-shaped data (JSON/YAML) | General-purpose | General-purpose |

**Choose merg when** you want strict type safety for config-shaped data with a Pythonic API inspired by Ruby's `deep_merge`. Choose `deepmerge` or `mergedeep` when you need flexibility with arbitrary Python types or strategy-based customization.

## Relationship to Ruby `deep_merge`

This library is inspired by the Ruby [`deep_merge`](https://github.com/danielsdeleo/deep_merge) gem, authored to be more Pythonic.

| Ruby `deep_merge` option | merg equivalent | Notes |
|---|---|---|
| Default recursive merge | `DeepMerge()` | Same behavior |
| `:preserve_unmergeables` | `preserve_mismatch=True` | Renamed for clarity |
| `:merge_nil_values` | `merge_none_value=True` | Python naming |
| `:overwrite_arrays` | `overwrite_list=True` | Python naming |
| `:extend_existing_arrays` | `extend_existing_list=True` | Python naming |
| `:sort_merged_arrays` | `sort_merged_list=True` | Python naming |
| `:uniq_arrays` | `deduplicate_list=True` | Python naming |
| `:knockout_prefix` | `knockout_prefix=...` | One removal form (`--x`); bare prefix is data |
| Block/proc | — | Not applicable in Python |

> **Trivia:** The Ruby `deep_merge` gem was the merge engine behind Puppet's Hiera data lookup system.

## Examples

### Config layering (defaults + environment + overrides)

```python
from merg import DeepMerge

defaults = {"app": {"debug": False, "timeout": 30, "workers": 4}}
env = {"app": {"debug": True, "timeout": 60}}
overrides = {"app": {"workers": 8}}

merg = DeepMerge()
config = merg.merge(defaults, env)
config = merg.merge(config, overrides)
# {"app": {"debug": True, "timeout": 60, "workers": 8}}
```

### Permission aggregation

```python
from merg import DeepMerge

base = {"permissions": ["read", "write"]}
admin = {"permissions": ["delete", "audit"]}

merg = DeepMerge(extend_existing_list=True, deduplicate_list=True)
result = merg.merge(base, admin)
# {"permissions": ["delete", "read", "audit", "write"]}
```

### Protecting sensitive paths

```python
from merg import DeepMerge

user = {"name": "alice", "internal": {"is_admin": False, "role": "user"}}
payload = {"name": "alice_updated", "internal": {"is_admin": True}}

merg = DeepMerge(exclude_paths=["internal"])
result = merg.merge(user, payload)
# {"name": "alice_updated", "internal": {"is_admin": False, "role": "user"}}
```

## License

MIT
