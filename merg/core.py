import logging
import copy
import ast
from .exceptions import InvalidTypeError

logger = logging.getLogger(__name__)


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
            "knockout_value": None,
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

        # Validate knockout_value against the same type contract the merge enforces.
        self._validate_tree(self.options["knockout_value"], ("knockout_value",))

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
        elif isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant):
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

        Top-level scalars are valid inputs: when both arguments are
        scalars, source wins (pass-through). When types differ at the
        top level, the mismatch rules apply as they do recursively.
        """
        self._validate_tree(target, ("target",))
        self._validate_tree(source, ("source",))
        return self._merge_recursive(target, source)

    def _validate_tree(self, value, path):
        """Recursively validate that every value in the tree is an allowed type."""
        if not isinstance(value, self.ALLOWED_TYPES):
            raise InvalidTypeError(
                f"Invalid type at '{_format_path(path)}': {_format_type(value)}"
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

        # Knockout: source equals prefix exactly -> replace with knockout_value
        ko_prefix = self.options["knockout_prefix"]
        if ko_prefix and isinstance(source, str) and source == ko_prefix:
            return copy.deepcopy(self.options["knockout_value"])

        # Handle None
        if source is None:
            if self.options["merge_none_value"]:
                return None
            return copy.deepcopy(target)

        # Type Mismatch
        if not isinstance(source, type(target)) and not (isinstance(source, (int, float)) and isinstance(target, (int, float))):
            if self.options["preserve_mismatch"]:
                return copy.deepcopy(target)
            return copy.deepcopy(source)

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
                result[key] = self._merge_recursive(result[key], value, current_path)
            else:
                # Knockout against a missing key: skip entirely (nothing to remove)
                if ko_prefix and isinstance(value, str) and value == ko_prefix:
                    continue
                result[key] = copy.deepcopy(value)

        return result

    def _merge_list(self, target, source, path):
        # Pre-scan source for knockout entries.
        ko_prefix = self.options["knockout_prefix"]
        knockout_matches = []
        if ko_prefix:
            stripped_source = []
            for item in source:
                if (isinstance(item, str)
                        and item.startswith(ko_prefix)
                        and item != ko_prefix):
                    knockout_matches.append(item[len(ko_prefix):])
                else:
                    stripped_source.append(item)
            source = stripped_source

        # Knockouts override list-strategy options. The semantics are
        # purely set-based: filter target by knockouts, then append
        # source non-knockouts. This matches Ruby's deep_merge gem.
        if knockout_matches:
            filtered_target = [t for t in target if t not in knockout_matches]
            result = [copy.deepcopy(t) for t in filtered_target]
            result.extend(copy.deepcopy(s) for s in source)
        elif self.options["overwrite_list"]:
            result = [copy.deepcopy(s) for s in source]
        elif self.options["extend_existing_list"]:
            result = []
            max_len = max(len(source), len(target))
            for i in range(max_len):
                if i < len(source) and (path + (i,)) not in self.options["exclude_paths"]:
                    result.append(copy.deepcopy(source[i]))
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

                    if not isinstance(s_item, type(t_item)) and not (isinstance(s_item, (int, float)) and isinstance(t_item, (int, float))):
                        if self.options["preserve_mismatch"]:
                            result.append(copy.deepcopy(t_item))
                            continue

                    result.append(self._merge_recursive(t_item, s_item, item_path))

                elif i < len(source):
                    # Source-only item: skip if its path is excluded.
                    if item_path in self.options["exclude_paths"]:
                        continue
                    result.append(copy.deepcopy(source[i]))
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
            try:
                result.sort()
            except TypeError:
                pass

        return result
