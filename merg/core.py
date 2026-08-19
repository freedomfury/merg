import ast
import contextlib
import copy
import datetime
import logging

from .exceptions import InvalidTypeError

logger = logging.getLogger(__name__)

# Sentinel returned when a merge removes the address instead of producing a
# value. _merge_dict pops the key on it; it never escapes merge().
_REMOVED = object()


def _format_path(path):
    """Format a path tuple as a human-readable dotted string."""
    if not path:
        return "<root>"
    parts = []
    for part in path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            if parts:
                parts.append(f".{part}")
            else:
                parts.append(str(part))
    return "".join(parts)


def _format_type(value):
    """Format a type name without the '<class ...>' wrapper."""
    return type(value).__name__


class DeepMerge:
    """
    Deep merges dictionaries with configurable strategies.
    Strictly adheres to JSON/YAML types (dict, list, str, int, float, bool, None).
    """

    ALLOWED_TYPES = (dict, list, str, int, float, bool, type(None))

    def __init__(self, **options):
        self.options = {
            "preserve_mismatch": False,
            "exclude_paths": [],
            "overwrite_list": False,
            "extend_existing_list": False,
            "deduplicate_list": False,
            "sort_merged_list": False,
            "merge_none_value": False,
            "knockout_prefix": "",
        }

        # Reject unknown option names so typos fail loudly instead of silently
        # being accepted and ignored (e.g. `extend_exsting_list=True`).
        unknown = sorted(set(options) - set(self.options))
        if unknown:
            raise TypeError(
                f"unknown option(s): {', '.join(unknown)}. "
                f"Valid options: {', '.join(sorted(self.options))}."
            )

        self.options.update(options)

        # Validate and normalize exclude_paths to a set of tuples.
        raw_paths = self.options["exclude_paths"]
        if not isinstance(raw_paths, (list, tuple, set)):
            raise TypeError(
                f"exclude_paths must be a list, tuple, or set; "
                f"got {_format_type(raw_paths)}."
            )
        normalized_paths = set()
        for p in raw_paths:
            if isinstance(p, str):
                normalized_paths.add(self._parse_path(p))
            elif isinstance(p, (list, tuple)):
                normalized_paths.add(tuple(p))
            else:
                raise TypeError(
                    f"exclude_paths entries must be str, list, or tuple; "
                    f"got {_format_type(p)}."
                )
        self.options["exclude_paths"] = normalized_paths

    def _parse_path(self, path_str):
        """
        Parses a Python-style path string into a tuple of keys.
        Supports dot notation (a.b.c) and bracket notation (a['b'][0]).
        Uses Python's built-in AST module for safe parsing, with a
        plain split('.') fallback for paths that aren't valid Python
        identifiers (e.g. dashes, slashes, keywords).
        """
        try:
            tree = ast.parse(path_str, mode='eval')
            return self._visit_node(tree.body)
        except (SyntaxError, ValueError):
            return tuple(path_str.split("."))

    def _visit_node(self, node):
        if isinstance(node, ast.Name):
            return (node.id,)
        elif isinstance(node, ast.Attribute):
            return self._visit_node(node.value) + (node.attr,)
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            index = node.slice.value
            return self._visit_node(node.value) + (index,)

        raise ValueError(f"Unsupported path syntax in: {node}")

    def merge(self, target, source):
        """
        Merges source into target.
        Target is not modified; a new merged structure is returned.

        Both target and source are recursively validated up front. If
        any value (at any depth) is not one of the allowed JSON/YAML
        types, an InvalidTypeError is raised before merging begins.

        The document root of both arguments must be a dict or a list;
        anything else raises InvalidTypeError. Scalars are valid
        everywhere else in the tree.
        """
        for name, value in (("target", target), ("source", source)):
            if not isinstance(value, (dict, list)):
                raise InvalidTypeError(
                    f"Top level must be dict or list; "
                    f"got {_format_type(value)} in {name}."
                )
        self._validate_tree(target, ("target",))
        self._validate_tree(source, ("source",))
        return self._merge_recursive(target, source)

    def _validate_tree(self, value, path):
        """Recursively validate that every value in the tree is an allowed type."""
        if not isinstance(value, self.ALLOWED_TYPES):
            hint = ""
            if isinstance(value, datetime.date):
                hint = (
                    " — YAML parsed this as a date; "
                    'quote it ("2026-08-18") to keep it a string'
                )
            raise InvalidTypeError(
                f"Invalid type at '{_format_path(path)}': {_format_type(value)}{hint}"
            )
        if isinstance(value, dict):
            for k, v in value.items():
                self._validate_tree(v, path + (k,))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                self._validate_tree(v, path + (i,))

    def _merge_recursive(self, target, source, path=()):
        if path in self.options["exclude_paths"]:
            return copy.deepcopy(target)

        # Knockout: source equals prefix exactly -> remove the address it occupies.
        ko_prefix = self.options["knockout_prefix"]
        if ko_prefix and isinstance(source, str) and source == ko_prefix:
            return _REMOVED

        # Handle None
        if source is None:
            if self.options["merge_none_value"]:
                return None
            return copy.deepcopy(target)

        # Type Mismatch
        if not isinstance(source, type(target)) and not (isinstance(source, (int, float)) and isinstance(target, (int, float))):
            if self.options["preserve_mismatch"]:
                return copy.deepcopy(target)
            # Route adopted source subtrees through the machinery so markers
            # are consumed (Finding 1) — a bare marker was already caught by
            # the knockout check above, so _copy_source can't return _REMOVED.
            return self._copy_source(source, path)

        # Merge Dictionaries
        if isinstance(source, dict):
            return self._merge_dict(target, source, path)

        # Merge Lists
        if isinstance(source, list):
            return self._merge_list(target, source, path)

        # Primitive Override
        return copy.deepcopy(source)

    def _merge_dict(self, target, source, path):
        result = copy.deepcopy(target)
        ko_prefix = self.options["knockout_prefix"]

        # Pre-scan source for key-level knockouts: a source key that starts with
        # the prefix (but isn't the prefix alone) strips the matching key from
        # target. Mirrors list-item knockout semantics: target-only, no-op if
        # the key doesn't exist. The value under a knockout key is ignored.
        knockout_keys = set()
        regular_items = []
        if ko_prefix:
            for key, value in source.items():
                if (isinstance(key, str)
                        and key.startswith(ko_prefix)
                        and key != ko_prefix):
                    knockout_keys.add(key[len(ko_prefix):])
                else:
                    regular_items.append((key, value))
        else:
            regular_items = list(source.items())

        # Apply knockouts first, then regular merges — so that
        # {"--a": "", "a": new} removes the old value and adds the new one.
        for stripped_key in knockout_keys:
            if (path + (stripped_key,)) in self.options["exclude_paths"]:
                continue
            result.pop(stripped_key, None)

        for key, value in regular_items:
            current_path = path + (key,)

            if current_path in self.options["exclude_paths"]:
                continue

            if key in result:
                merged = self._merge_recursive(result[key], value, current_path)
                if merged is _REMOVED:
                    del result[key]
                else:
                    result[key] = merged
            else:
                # Knockout against a missing key: skip entirely (nothing to remove)
                if ko_prefix and isinstance(value, str) and value == ko_prefix:
                    continue
                result[key] = self._copy_source(value, current_path)

        return result

    def _copy_source(self, value, path):
        """
        Copy a source value that has no target counterpart.

        Containers still pass through the merge machinery so knockout
        tokens inside them are consumed rather than copied into the
        result; scalars copy verbatim.
        """
        if isinstance(value, dict):
            return self._merge_dict({}, value, path)
        if isinstance(value, list):
            return self._merge_list([], value, path)
        return copy.deepcopy(value)

    def _merge_list(self, target, source, path):
        # Pre-scan source for knockout entries. A bare prefix wipes the
        # whole target list; a payload entry (--x) removes target items
        # equal to x.
        ko_prefix = self.options["knockout_prefix"]
        wipe = False
        knockout_matches = []
        indexed_source = []
        for i, item in enumerate(source):
            if ko_prefix and isinstance(item, str) and item.startswith(ko_prefix):
                if item == ko_prefix:
                    wipe = True
                else:
                    knockout_matches.append(item[len(ko_prefix):])
            else:
                indexed_source.append((i, item))

        # Knockouts override list-strategy options. The semantics are
        # purely set-based: wipe or filter the target, then append the
        # remaining source items. Position within the source list is
        # irrelevant. (exclude_paths is not consulted here yet — Bug 2.)
        if ko_prefix and (wipe or knockout_matches):
            if wipe:
                result = []
            else:
                result = [copy.deepcopy(t) for t in target if t not in knockout_matches]
            result.extend(
                self._copy_source(item, path + (i,)) for i, item in indexed_source
            )
        elif self.options["overwrite_list"]:
            result = [self._copy_source(s, path + (i,)) for i, s in enumerate(source)]
        elif self.options["extend_existing_list"]:
            result = []
            max_len = max(len(source), len(target))
            for i in range(max_len):
                if i < len(source) and (path + (i,)) not in self.options["exclude_paths"]:
                    result.append(self._copy_source(source[i], path + (i,)))
                if i < len(target):
                    result.append(copy.deepcopy(target[i]))
        else:
            result = []
            max_len = max(len(source), len(target))
            for i in range(max_len):
                item_path = path + (i,)

                if i < len(source) and i < len(target):
                    # Both sides exist: recurse so exclude_paths fires correctly.
                    s_item = source[i]
                    t_item = target[i]

                    result.append(self._merge_recursive(t_item, s_item, item_path))

                elif i < len(source):
                    # Source-only item: skip if its path is excluded.
                    if item_path in self.options["exclude_paths"]:
                        continue
                    result.append(self._copy_source(source[i], item_path))
                else:
                    # Target-only item: always preserved (exclude_paths controls
                    # what source can write, not what target retains).
                    result.append(copy.deepcopy(target[i]))

        if self.options["deduplicate_list"]:
            try:
                result = list(dict.fromkeys(result))
            except TypeError:
                unique = []
                for x in result:
                    if x not in unique:
                        unique.append(x)
                result = unique

        if self.options["sort_merged_list"]:
            with contextlib.suppress(TypeError):
                result.sort()

        return result
