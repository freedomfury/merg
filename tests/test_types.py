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


def test_top_level_root_must_be_dict_or_list():
    """The document root must be a container; scalar and None roots are rejected."""
    merger = DeepMerge()

    with pytest.raises(InvalidTypeError):
        merger.merge(1, 2)
    with pytest.raises(InvalidTypeError):
        merger.merge("old", "new")
    with pytest.raises(InvalidTypeError):
        merger.merge(None, {})
    with pytest.raises(InvalidTypeError):
        merger.merge({}, 5)


def test_top_level_none_handling_within_containers():
    """None inside the tree still follows merge_none_value."""
    merger = DeepMerge()
    assert merger.merge({"a": "keep"}, {"a": None}) == {"a": "keep"}

    merger_n = DeepMerge(merge_none_value=True)
    assert merger_n.merge({"a": "keep"}, {"a": None}) == {"a": None}


def test_none_target_is_absent_not_protected():
    """Q10: a blank YAML key or stubbed section parses to None in the base —
    a patch supplying the real value must not be blocked by preserve_mismatch."""
    m = DeepMerge(preserve_mismatch=True)
    assert m.merge({"port": None}, {"port": 8080}) == {"port": 8080}
    assert m.merge({"db": None}, {"db": {"h": "x"}}) == {"db": {"h": "x"}}
    assert m.merge({"db": None}, {"db": [1, 2]}) == {"db": [1, 2]}


def test_none_patch_side_unchanged():
    """Source-side None semantics are untouched by Q10."""
    assert DeepMerge().merge({"a": 5}, {"a": None}) == {"a": 5}
    assert DeepMerge(merge_none_value=True).merge({"a": 5}, {"a": None}) == {"a": None}
    assert DeepMerge().merge({"a": None}, {"a": None}) == {"a": None}


def test_none_target_adoption_is_verbatim():
    """Q10 adoption uses plain deepcopy — a bare marker is data, not a token."""
    m = DeepMerge(knockout_prefix="--", preserve_mismatch=True)
    assert m.merge({"a": None}, {"a": ["--"]}) == {"a": ["--"]}
    assert m.merge({"a": None}, {"a": {"b": "--"}}) == {"a": {"b": "--"}}


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


def test_date_types_rejected_with_quoting_hint():
    """Dates stay invalid by design; the error points at the YAML quoting fix."""
    import datetime

    merger = DeepMerge()
    with pytest.raises(InvalidTypeError, match="quote it"):
        merger.merge({}, {"deploy_date": datetime.date(2026, 8, 18)})
    with pytest.raises(InvalidTypeError, match="quote it"):
        merger.merge({"start": datetime.datetime(2026, 8, 18, 10, 0)}, {})
