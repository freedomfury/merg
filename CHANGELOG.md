# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
