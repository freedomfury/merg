# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2026-08-19

### Changed

- Knockout has one form: the prefix plus a name. `--a` as a dict key removes key `a` — the value under it is ignored, any type works. `--x` as a list item removes base items whose value equals `x`, all occurrences, wherever they sit. A bare prefix is data everywhere: `{'a': '--'}` assigns the two-character string, `['--']` merges as an ordinary list item, and `{'--': 'y'}` adds a key literally named `--`. Removal addresses values, not positions — `--0` does not remove a list's first element. This replaces 0.0.2's behavior, where a bare marker as a dict value nulled the key instead.
- If a patch dict contains both `--a` and `a`, the knockout runs first and `a` is then inserted fresh rather than deep-merged into the old value. This is how you replace a nested dict outright.
- The document root passed to `merge()` must be a `dict` or `list`; anything else raises `InvalidTypeError`. Merging two scalars returned the second argument unchanged, which is not a merge. Scalars remain valid everywhere else in the tree.
- `exclude_paths` filters the patch only: the named paths are removed from the patch before merging, and whatever remains merges by the ordinary rules. It previously mixed two behaviors — filtering the patch for dict keys while protecting base list items at excluded indices. Two consequences of the single rule: dropping a patch list element shifts the ones after it one slot earlier, and `a` and `--a` are different keys, so blocking both removal spellings means excluding both.
- `date`/`datetime` remain invalid types by design. YAML's implicit timestamp resolution (`2026-08-18` unquoted — common in Ansible and `yaml.safe_load` pipelines) is the usual source; the `InvalidTypeError` message now says to quote the value, and the README documents the pitfall.
- The README documents the inherent limits of a string-prefix scheme: removal matches string values only, so integers and lists of dicts have no removal form; and data whose string starts with the prefix is read as an instruction, so `args: ["--quiet"]` in a patch removes an item named `quiet` rather than adding a flag. `knockout_prefix` is configurable precisely so this can be avoided. Avoid `&`, `*`, `!`, `#`, `~`, and `@` as prefixes in YAML — anchor, alias, tag, comment, null, and reserved indicators.

### Removed

- The `knockout_value` option. A marker that substitutes a construction-time constant is strictly less expressive than writing the value directly; absence is the only thing a plain value cannot express, and removal covers it. No deprecation shim — passing `knockout_value` fails as an unknown option.

### Fixed

- `_merge_list` disagreed with `_merge_dict` when `preserve_mismatch=True` and the patch value was `None`. The index-merge loop ran its own type-mismatch check before `_merge_recursive` could resolve it, so `merge([5], [None])` kept the base while `merge({"a": 5}, {"a": None})` took the `None`. The duplicated check is deleted — `_merge_recursive` is now the single definition of merge precedence — and behavior on every other path is unchanged.
- `exclude_paths` had no effect in knockout list mode: the knockout branch never consulted it, so excluding index 0 and index 1 produced identical results. Filtering the patch before merging removes the interaction entirely — excluded entries never reach knockout processing.
- A `None` base value is absent, not a value worth protecting. YAML turns a blank key or a stubbed section into `None`; under `preserve_mismatch=True` that accidental `None` blocked the patch supplying the real value, so `{'port': None} + {'port': 8080}` stayed `None`. The patch now fills it. Patch-side `None` semantics (`merge_none_value`) are unchanged — the two sides now agree that a `None` is not a value worth defending.
- Lint was red (13 violations) and `ruff` was unpinned in CI and the Makefile, so a new ruff release could redden CI on its own. Added `[tool.ruff]` to `pyproject.toml` with an explicit rule selection (`E4`, `E7`, `E9`, `F`, `I`, `SIM`, `PIE`) and `target-version = "py310"` — an explicit `select` means the rule set cannot drift with ruff's defaults — and pinned `ruff@0.16.3` in both CI and the Makefile. Violations fixed: import sorting across the package and tests, unnecessary `pass` statements in `exceptions.py`, a collapsible nested `if` in `_visit_node`, and the sort fallback now uses `contextlib.suppress(TypeError)`.
- Test suite rebuilt around the two-rule knockout model, the root contract, and patch-side `exclude_paths` (125 total; was 113).

## [0.0.2] - 2026-04-18

### Added

- Dict key knockout: when `knockout_prefix` is set, a source key prefixed with the marker (e.g. `"--a"`) removes the matching key from the target dict entirely. Mirrors existing list-item knockout behavior. The value under a knockout key is irrelevant and discarded. Knockouts within a source dict are applied before regular merges, so `{"--a": None, "a": new_val}` cleanly replaces the old value rather than deep-merging into it. Respects `exclude_paths`.
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
