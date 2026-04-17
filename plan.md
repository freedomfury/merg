# Review Request: `merger` library (pre-publish polish)

## Context

This is a Python library I want to publish to PyPI as `merger`. The package is a namespace for merge implementations; the first (and currently only) implementation is `DeepMerge`. The library ports the semantics of the Ruby `deep_merge` gem (Steve Midgley / Daniel DeLeo) into Python, with strict JSON/YAML-shaped type validation added.

The code exists, tests pass (35/35), architecture is clean. I need a polish pass and packaging review before publishing 0.1.0.

## Positioning

Please honor these framing decisions — they are settled:

- The library is positioned as a **Python port of the Ruby `deep_merge` gem's semantics**, NOT as "Hiera-inspired." Hiera was a consumer of deep_merge, not its origin. Crediting the actual lineage is more accurate and attracts a broader audience.
- Scope is deliberately narrow: structured data consisting of `dict`, `list`, `str`, `int`, `float`, `bool`, and `None` — the common subset of JSON/YAML/TOML and hand-built Python data. This narrowness is a feature; don't generalize it.
- The package name is `merger`. The primary class is `DeepMerge`. Framing: "DeepMerge is one type of merge; merger is the library that holds merge types." Leaves room for future `QuickMerge` or similar without committing to build them.

## Current State

### Package layout

```
deep-merge/
├── deep_merge/
│   ├── __init__.py
│   ├── core.py
│   └── exceptions.py
├── tests/
│   ├── test_deep_merge.py       # data-driven from test_data.yml
│   ├── test_data.yml            # 23 parameterized cases
│   ├── test_fixes.py
│   ├── test_path_parsing.py
│   └── test_types.py
├── examples/
│   └── deepmerge.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### Test status
35/35 passing. Data-driven YAML test cases cover list strategies, knockout-style scenarios, type mismatches, null handling, exclusion paths (AST-parsed with dot and bracket notation), and edge cases.

### Implementation highlights
- `DeepMerge` is stateless after construction: instantiate with options, call `merge(target, source)` many times.
- Strict type validation via `ALLOWED_TYPES = (dict, list, str, int, float, bool, type(None))`. Invalid types raise `InvalidTypeError`.
- Uses `copy.deepcopy` throughout — inputs are never mutated.
- AST-based path parser for `exclude_paths` supports `"a.b.c"`, `"server['config']['port']"`, `"servers[0].name"`, and falls back to `split('.')` on parse failure.
- Knockout-prefix semantics from the Ruby gem are preserved.

## Known Issues to Address

Please evaluate each of these and recommend fixes. Feel free to flag anything else you find.

### 1. Rename package directory
Currently `deep_merge/` — needs to become `merger/`. Update:
- Directory rename
- `pyproject.toml`: `name = "merger"`, `packages = ["merger"]`
- All import statements in tests and examples
- `__init__.py` exports
- README code examples

Keep the class name `DeepMerge` — don't rename the class. It's descriptive and doesn't collide with the package name.

### 2. Placeholder author info
`pyproject.toml` has:
```
authors = [{name = "Antigravity", email = "antigravity@google.com"}]
```
Obvious AI artifact. Replace with my real info (I'll provide when doing the edit).

### 3. Dead option
`merge_dict_list` is declared in `__init__` defaults but never referenced anywhere in `core.py`. Either implement it (if there's a clear intended semantic — I don't recall what it was supposed to do) or remove it from defaults to avoid misleading users reading the options list.

### 4. Misleading docstring
In `core.py`, `merge()`'s docstring says:
> "The target is NOT modified in-place to allow for immutable types in recursion, but the result should be assigned back to the target."

The second half is wrong — since deepcopy is used, the caller does not need to assign the result back to target. Target is untouched. Rewrite to: "Target is not modified; a new merged structure is returned."

### 5. Legacy Python compat
Line 63-65 in `core.py` has `ast.Index` / `ast.Str` / `ast.Num` handling for Python < 3.9. `pyproject.toml` declares `requires-python = ">=3.8"` but 3.8 and 3.9 are EOL. Recommend bumping the minimum to 3.10 or 3.11 and deleting the legacy branches. Simpler code, reflects reality.

### 6. Top-level scalar behavior
Currently `DeepMerge().merge(1, 2)` returns `2` — top-level scalars merge with source-wins. Decide: document this as intentional pass-through behavior, or raise an error at `merge()` entry when either argument isn't a `dict` or `list`. Either is defensible. I lean toward documenting it as intentional since rejecting would require inconsistent handling between top-level and recursive calls.

### 7. Logging consistency
Mix of `logger.debug` (named logger) and `logging.debug` (root logger) in earlier versions — please audit current `core.py` and normalize to `logger.debug` throughout.

### 8. Error message polish
`InvalidTypeError` messages include raw tuples for paths, e.g. `"Invalid type at ('a', 'b'): <class 'set'>"`. Consider formatting as `"Invalid type at 'a.b': set"` for human readability.

### 9. Bool-vs-int edge case
`isinstance(True, int) is True` in Python creates subtle type-mismatch behavior. Current code works correctly (via the `(int, float)` escape hatch on line 103), but the behavior is implicit. Add an explicit test case documenting what happens when merging `{"a": True}` with `{"a": 1}` and vice versa.

### 10. Commented stale code
Check for any commented-out imports or dead TODO comments that should just be deleted. Git history preserves them if ever needed.

## README Rewrite

The current README is minimal. Please rewrite to:

- Lead with "A Python port of the Ruby `deep_merge` gem's semantics, with strict JSON/YAML-shaped type validation."
- Include a "Type scope" table showing what's supported: `dict`, `list`, `str`, `int`, `float`, `bool`, `None`. Explicitly note that `set`, `tuple`, `datetime`, `frozenset`, etc. are NOT supported and will raise `InvalidTypeError`.
- Include a "Why merger vs other libraries?" section honestly contrasting with `deepmerge` (popular, strategy-based, less strict) and `mergedeep` (actively maintained, different API). The positioning is: "this library is strict about types by design; it's specifically for config-shaped data; it preserves the Ruby gem's merge semantics including knockout prefix."
- Keep the existing options table but expand each option with a short concrete example.
- Add a "Relationship to Ruby deep_merge" section with a table showing which options match the Ruby gem and which are additions or differences.
- Include Hiera/Puppet lineage briefly as a "trivia" footnote — not as primary framing. Something like: "The Ruby `deep_merge` gem was the merge engine behind Puppet's Hiera data lookup system; this library brings those semantics to Python."
- Several small, runnable examples showing common use cases.

## Packaging checklist

Please verify or fix:

- `pyproject.toml` has all needed metadata: name, version, description, authors, readme, license, Python classifiers, dev-status classifier
- `LICENSE` file is present and referenced
- `CHANGELOG.md` exists (even if minimal — initial release note)
- Version set to `0.1.0`
- Build backend (`hatchling`) is correctly configured for the new package name
- No stray Mac metadata files (`._*`), `__pycache__` directories, or `.pytest_cache` in the published source distribution (should be gitignored and excluded from sdist/wheel)

## Things NOT to do

- Do not rename the class from `DeepMerge` to something else.
- Do not add features not currently in the code. Polish only. New features wait for 0.2.
- Do not broaden the type scope. Sets, tuples, datetimes, etc. remain unsupported by design.
- Do not add configuration for Hiera compatibility. The library is its own thing that happens to share semantics with the Ruby gem.
- Do not restructure into a strategy-pattern API to match `deepmerge` (toumorokoshi's) design. The options-dict API is intentional.
- Do not add pluggable backends, custom type registries, or any extension mechanism at this stage. Keep it small.

## Deliverables

After your review, I expect:

1. A concrete list of changes to make, organized by file.
2. Proposed new content for the README.
3. Proposed `pyproject.toml` with corrected metadata.
4. A `CHANGELOG.md` entry for 0.1.0.
5. Any additional test cases you recommend (especially for bool/int interaction, empty inputs, mixed-type sort failure, top-level list merging).
6. A publishing checklist specific to this library, including PyPI name verification and TestPyPI dry-run steps.

## Followup (not in scope for this review)

After `merger` 0.1.0 is published, there's a larger service — working name **Rung** — that will be built on top of it. Rung is a fact-based config lookup service (think: Hiera-behind-an-API, but scoped to "given these facts, what's this value"). Don't design or discuss Rung here — that's a separate conversation after the library ships. Mentioned only so you understand the broader context: the library is a foundation being shipped ahead of the service that consumes it.
