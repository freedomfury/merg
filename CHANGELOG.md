# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2026-08-18

### Changed

- Knockout semantics simplified to removal. A bare `knockout_prefix` marker (e.g. `"--"`) now removes the thing at the address it occupies instead of substituting a configured constant. In dicts, the key is removed — `{'a': 5} + {'a': '--'}` → `{}`. In lists, a bare marker wipes the target list and the remaining source items append, position-independent: `[1, 2, 3] + ['--', '9']` → `['9']`. The payload form (`--x`) is unchanged: it removes by value, wherever the target item sits. Removal never cascades — removing the last key of a nested dict leaves an empty dict.
- The document root passed to `merge()` must now be a `dict` or `list`; anything else raises `InvalidTypeError`. Scalars remain valid everywhere else in the tree.
- Knockout tokens are consumed, never copied: source containers pass through the merge machinery even when the target has no counterpart, so merged results contain no marker strings when `knockout_prefix` is set. Markers in *target* data are literal — only source is interpreted.
- `date`/`datetime` remain invalid types by design. YAML's implicit timestamp resolution (`2026-08-18` unquoted — common in Ansible and `yaml.safe_load` pipelines) is the usual source; the `InvalidTypeError` message now says to quote the value, and the README documents the pitfall.

### Removed

- The `knockout_value` option. A marker that substitutes a construction-time constant is strictly less expressive than writing the value directly; absence is the only thing plain values cannot express, and removal now covers it. No deprecation shim — passing `knockout_value` fails as an unknown option.

### Fixed

- `_merge_list` disagreed with `_merge_dict` when `preserve_mismatch=True` and the source value was a knockout marker or `None`. The default index-merge loop ran its own type-mismatch check before `_merge_recursive` could resolve those sentinels, so `merge([5], ["--"])` kept the target while `merge({"a": 5}, {"a": "--"})` knocked out. The duplicated check is deleted — `_merge_recursive` is now the single definition of merge precedence — and behavior on every other path is unchanged.
- Bug 3: a bare marker no longer survives into results as a literal string (`merge([], ['--', 'a'])` was `['--', 'a']`, now `['a']`).
- Finding 1: the type-mismatch branch in `_merge_recursive` adopted source subtrees wholesale via `deepcopy`, leaking bare markers into results — `{'a': 5} + {'a': ['--']}` was `{'a': ['--']}`, now `{'a': []}`. The third wholesale-adoption path (alongside new dict keys and source-only list items) now routes through the same machinery, so markers are consumed everywhere.
- Bug 4: lint was red (13 violations) and `ruff` was unpinned in CI and the Makefile, so lint drift on a new ruff release would redden CI. Added `[tool.ruff]` to `pyproject.toml` with an explicit rule selection (`E4`, `E7`, `E9`, `F`, `I`, `SIM`, `PIE`) and `target-version = "py310"` — an explicit `select` means the rule set can't drift with ruff's defaults — and pinned `ruff@0.16.3` in both CI and the Makefile. Violations fixed: import sorting across the package and tests, unnecessary `pass` statements in `exceptions.py`, a collapsible nested `if` in `_visit_node`, and the sort fallback now uses `contextlib.suppress(TypeError)`.
- Knockout tests rewritten for removal semantics, plus new wipe/root/invariant coverage, a whole-result marker-leak sweep, and YAML cases uc132–uc134 (129 total; was 113).

## [0.0.2] - 2026-04-18

### Added

- Dict key knockout: when `knockout_prefix` is set, a source key prefixed with the marker (e.g. `"--a"`) removes the matching key from the target dict entirely. Mirrors existing list-item knockout behavior and matches Hiera/Puppet semantics. The value under a knockout key is irrelevant and discarded. Knockouts within a source dict are applied before regular merges, so `{"--a": None, "a": new_val}` cleanly replaces the old value rather than deep-merging into it. Respects `exclude_paths`.
- 13 new tests covering dict key knockout (113 total).
- `Makefile` for development automation. Targets: `venv`, `lint`, `tests`, `test` (default — lint + tests), `build`, `deploy` (pushes release tag → PyPI), `clean`. Uses strict bash (`.ONESHELL`, `-eu -o pipefail`). `deploy` runs the full test suite first and guards against uncommitted changes.
- TestPyPI publishing changed to manual-only via `workflow_dispatch` (Run workflow button in GitHub Actions). No RC tags needed.
- `publish-pypi.yml` publish job now references the `pypi` GitHub environment for trusted publishing access control.

## [0.0.1] - 2026-04-17

Initial release.

### Added

- `DeepMerge` class for recursive merging of JSON/YAML-shaped data structures.
- Strict type validation: only `dict`, `list`, `str`, `int`, `float`, `bool`, and `None` are accepted. Both target and source are validated recursively up front; any unsupported type at any depth raises `InvalidTypeError`.
- Configurable merge options:
  - `preserve_mismatch` — keep target value on type mismatch instead of source-wins.
  - `exclude_paths` — skip specific paths during merge. Accepts dot notation (`"a.b.c"`), bracket notation (`"users[0]['name']"`), and raw tuples (`("k8s.io", "name")`). Falls back gracefully for keys that aren't valid Python identifiers (dashes, slashes, keywords).
  - `overwrite_list` — replace target list entirely with source list.
  - `extend_existing_list` — interleave source and target list items.
  - `deduplicate_list` — remove duplicate items after merging lists.
  - `sort_merged_list` — sort list items after merging (silently skipped for incomparable types).
  - `merge_none_value` — allow `None` in source to overwrite target values.
  - `knockout_prefix` / `knockout_value` — mark source values for removal. In lists, items prefixed with the marker (e.g. `"--foo"`) remove matching items from target; the result is set-style (filtered target + appended source non-knockouts), matching the Ruby `deep_merge` gem. In dicts and at the top level, a value equal to the marker exactly is replaced with `knockout_value` (default `None`).
- Unknown option names are rejected at construction time with a descriptive `TypeError`, so typos like `extend_exsting_list=True` fail loudly instead of silently being ignored.
- Immutable merge semantics: inputs are never mutated; `copy.deepcopy` is applied throughout, including in the `preserve_mismatch` list path.
- Data-driven test suite of 31 parameterized YAML cases, plus targeted unit tests for type validation, path parsing, knockout semantics, exclude paths across all list-merge modes, and option validation. 100 tests total.
