import logging
import copy
import ast
from .exceptions import InvalidTypeError

logger = logging.getLogger(__name__)

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
            "merge_dict_list": False,
            "merge_none_value": False,
        }
        self.options.update(options)

        # Normalize exclude_paths to set of tuples
        normalized_paths = set()
        for p in self.options["exclude_paths"]:
            if isinstance(p, str):
                normalized_paths.add(self._parse_path(p))
            else:
                # Assume iterable (list/tuple)
                normalized_paths.add(tuple(p))
        self.options["exclude_paths"] = normalized_paths

    def _parse_path(self, path_str):
        """
        Parses a Python-style path string into a tuple of keys.
        Supports dot notation (a.b.c) and bracket notation (a['b'][0]).
        Uses Python's built-in AST module for safe parsing.
        """
        try:
            tree = ast.parse(path_str, mode='eval')
            return self._visit_node(tree.body)
        except SyntaxError:
            # Fallback for simple dot strings that might fail AST (e.g. if they start with number?)
            # though standard variable names shouldn't.
            # If it fails, maybe it is just a simple dotted string user intended?
            return tuple(path_str.split("."))

    def _visit_node(self, node):
        if isinstance(node, ast.Name):
            return (node.id,)
        elif isinstance(node, ast.Attribute):
            return self._visit_node(node.value) + (node.attr,)
        elif isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant): # Python 3.9+ for string/int literals
                index = node.slice.value
                return self._visit_node(node.value) + (index,)
            elif isinstance(node.slice, ast.Index): # Python < 3.9
                 if isinstance(node.slice.value, (ast.Str, ast.Num)):
                     return self._visit_node(node.value) + (node.slice.value.n if isinstance(node.slice.value, ast.Num) else node.slice.value.s,)
        
        raise ValueError(f"Unsupported path syntax in: {node}")

    def merge(self, target, source):
        """
        Merges source into target.
        Note: The target is NOT modified in-place to allow for immutable types in recursion,
        but the result should be assigned back to the target.
        """
        self._validate_type(target, "target")
        self._validate_type(source, "source")
        return self._merge_recursive(target, source)

    def _validate_type(self, value, label):
        if not isinstance(value, self.ALLOWED_TYPES):
            raise InvalidTypeError(f"{label} has invalid type: {type(value)}")

    def _merge_recursive(self, target, source, path=()):
        # Handle Exclusion
        if path in self.options["exclude_paths"]:
             # This logic is better handled by caller (iterating source keys), 
             # but if we get here with an excluded value, we can return target?
             # Actually, dict iteration handles this. This is fallback.
             return copy.deepcopy(target)

        # Type Validation (Strict)
        # Note: None is allowed if in ALLOWED_TYPES. 
        if not isinstance(source, self.ALLOWED_TYPES):
             raise InvalidTypeError(f"Invalid type at {path}: {type(source)}")

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
        
        for key, value in source.items():
            current_path = path + (key,)
            
            if current_path in self.options["exclude_paths"]:
                continue
                
            if key in result:
                # Validating strict target types on recursion
                self._validate_type(result[key], f"target[{key}]")
                result[key] = self._merge_recursive(result[key], value, current_path)
            else:
                self._validate_type(value, current_path)
                result[key] = copy.deepcopy(value)
                
        return result

    def _merge_list(self, target, source, path):
        if self.options["overwrite_list"]:
            return copy.deepcopy(source)

        result = []
        
        if self.options["extend_existing_list"]:
            # Interleave
            max_len = max(len(source), len(target))
            for i in range(max_len):
                if i < len(source):
                    result.append(copy.deepcopy(source[i]))
                if i < len(target):
                    result.append(copy.deepcopy(target[i]))
        else:
            # Overwrite by Index
            max_len = max(len(source), len(target))
            for i in range(max_len):
                if i < len(source) and i < len(target):
                    s_item = source[i]
                    t_item = target[i]
                    
                    # Check type mismatch for list items strictly
                    if not isinstance(s_item, type(t_item)) and not (isinstance(s_item, (int, float)) and isinstance(t_item, (int, float))):
                        if self.options["preserve_mismatch"]:
                            result.append(t_item)
                            continue
                    
                    # Recurse or overwite
                    # We always recurse to handle nested structures or logic like merge_none_value
                    result.append(self._merge_recursive(t_item, s_item, path + (i,)))

                elif i < len(source):
                    result.append(copy.deepcopy(source[i]))
                else:
                    # Keep extra target items
                    result.append(copy.deepcopy(target[i]))

        if self.options["deduplicate_list"]:
            try:
                # Use dict.fromkeys to preserve order
                result = list(dict.fromkeys(result))
            except TypeError:
                # Fallback for unhashables (dicts/lists)
                unique = []
                for x in result:
                    if x not in unique:
                        unique.append(x)
                result = unique

        if self.options["sort_merged_list"]:
            try:
                result.sort()
            except TypeError:
                # If mixed types, ignore sort failure
                pass

        return result
