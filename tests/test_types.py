import pytest
from merg import DeepMerge, InvalidTypeError
from merg.core import _format_path


def test_format_path_empty_returns_root():
    """Defensive branch: empty path tuples format as '<root>'."""
    assert _format_path(()) == "<root>"

def test_strict_type_validation():
    merger = DeepMerge()
    
    # Valid types
    assert merger.merge({"a": 1}, {"a": 2}) == {"a": 2}
    
    # Invalid Source Type (Set)
    with pytest.raises(InvalidTypeError):
        merger.merge({"a": 1}, {"a": {1, 2}})
        
    # Invalid Target Type (Tuple)
    with pytest.raises(InvalidTypeError):
        merger.merge({"a": (1, 2)}, {"a": 1})
        
    # Invalid Nested Type
    with pytest.raises(InvalidTypeError):
        merger.merge({"a": [1]}, {"a": [set()]})

def test_type_mismatch_preserve():
    merger = DeepMerge(preserve_mismatch=True)
    # Int vs String -> Mismatch -> Keep Target
    assert merger.merge({"a": 1}, {"a": "2"}) == {"a": 1}

def test_type_mismatch_overwrite():
    merger = DeepMerge(preserve_mismatch=False)
    # Int vs String -> Mismatch -> Overwrite with Source
    assert merger.merge({"a": 1}, {"a": "2"}) == {"a": "2"}


def test_bool_int_merge():
    """bool is a subclass of int in Python (isinstance(True, int) is True).
    The (int, float) escape hatch in type-mismatch detection treats bool
    and int as compatible, so source wins without triggering mismatch logic."""
    merger = DeepMerge()

    # bool source into int target — source wins (both in int/float group)
    assert merger.merge({"a": 1}, {"a": True}) == {"a": True}

    # int source into bool target — source wins
    assert merger.merge({"a": True}, {"a": 1}) == {"a": 1}

    # With preserve_mismatch: still no mismatch detected (int/float group)
    merger_p = DeepMerge(preserve_mismatch=True)
    assert merger_p.merge({"a": 1}, {"a": True}) == {"a": True}
    assert merger_p.merge({"a": True}, {"a": 0}) == {"a": 0}


def test_top_level_scalars():
    """Top-level scalars merge with source-wins semantics (pass-through)."""
    merger = DeepMerge()

    assert merger.merge(1, 2) == 2
    assert merger.merge("old", "new") == "new"
    assert merger.merge(1.0, 2.5) == 2.5
    assert merger.merge(True, False) is False


def test_top_level_none_handling():
    """None at top level follows merge_none_value option."""
    merger = DeepMerge()
    assert merger.merge("keep", None) == "keep"

    merger_n = DeepMerge(merge_none_value=True)
    assert merger_n.merge("keep", None) is None


def test_top_level_type_mismatch():
    """Top-level type mismatch follows preserve_mismatch option."""
    merger = DeepMerge()
    assert merger.merge(1, "two") == "two"  # source wins

    merger_p = DeepMerge(preserve_mismatch=True)
    assert merger_p.merge(1, "two") == 1  # target kept


def test_top_level_list_merge():
    """Top-level lists merge with the same strategies as nested lists."""
    merger = DeepMerge()
    assert merger.merge(["a", "b"], ["x", "y"]) == ["x", "y"]

    merger_e = DeepMerge(extend_existing_list=True)
    assert merger_e.merge(["a", "b"], ["x", "y"]) == ["x", "a", "y", "b"]


def test_empty_inputs():
    """Empty dicts and lists merge correctly."""
    merger = DeepMerge()
    assert merger.merge({}, {"a": 1}) == {"a": 1}
    assert merger.merge({"a": 1}, {}) == {"a": 1}
    assert merger.merge({}, {}) == {}
    assert merger.merge([], [1, 2]) == [1, 2]
    assert merger.merge([1, 2], []) == [1, 2]
    assert merger.merge([], []) == []


# -----------------------------------------------------------------------------
# Bug #5 — eager (recursive) target/source validation
# -----------------------------------------------------------------------------

def test_invalid_type_in_untouched_target_key_is_rejected():
    """Eager validation: bad types anywhere in target raise, even if source doesn't touch them."""
    merger = DeepMerge()
    with pytest.raises(InvalidTypeError):
        merger.merge({"a": 1, "untouched": {1, 2, 3}}, {"a": 99})


def test_invalid_type_deeply_nested_in_target_is_rejected():
    """Validation walks the full tree."""
    merger = DeepMerge()
    bad_target = {"top": {"middle": {"deep": (1, 2)}}}  # tuple, not allowed
    with pytest.raises(InvalidTypeError):
        merger.merge(bad_target, {})


def test_invalid_type_inside_target_list_is_rejected():
    """Validation walks list items too."""
    merger = DeepMerge()
    with pytest.raises(InvalidTypeError):
        merger.merge({"items": [1, 2, {1, 2}]}, {"items": [9]})


def test_invalid_type_in_source_is_rejected():
    """Symmetric: source is also walked."""
    merger = DeepMerge()
    with pytest.raises(InvalidTypeError):
        merger.merge({"a": 1}, {"a": {"nested": (1, 2)}})


def test_valid_deeply_nested_target_passes():
    """Sanity check: a clean nested target still merges."""
    merger = DeepMerge()
    target = {
        "level1": {
            "level2": {"level3": [1, 2, {"k": "v"}]},
            "other": True,
        },
        "scalars": [None, 1, 1.5, "str", False],
    }
    result = merger.merge(target, {"scalars": [99]})
    assert result["scalars"][0] == 99
    assert result["level1"]["level2"]["level3"] == [1, 2, {"k": "v"}]
