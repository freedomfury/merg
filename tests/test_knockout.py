import pytest
from merg import DeepMerge, InvalidTypeError


# -----------------------------------------------------------------------------
# Top-level scalar knockout
# -----------------------------------------------------------------------------

def test_top_level_scalar_knockout_to_none():
    """Source equals prefix exactly at top level -> result is knockout_value (default None)."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([1, 2, 3], "--") is None


def test_top_level_scalar_knockout_custom_value():
    """knockout_value can be customized."""
    merg = DeepMerge(knockout_prefix="--", knockout_value="REMOVED")
    assert merg.merge([1, 2, 3], "--") == "REMOVED"


# -----------------------------------------------------------------------------
# List knockout
# -----------------------------------------------------------------------------

def test_list_knockout_removes_matching_target_item():
    """Ruby semantics: filter target by knockouts, then append source non-knockouts."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["one", "two", "three"], ["--one", "four"])
    assert result == ["two", "three", "four"]


def test_list_knockout_strips_only_knockout_entries():
    """Knockout entries themselves are stripped from the result."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b"], ["--a"])
    assert result == ["b"]


def test_list_knockout_no_match_is_safe():
    """Knocking out a non-existent item is a no-op."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b"], ["--zzz"])
    assert result == ["a", "b"]


def test_list_knockout_preserves_target_order():
    """Target items stay in their original order; source items append after."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b", "c", "d"], ["--c", "e"])
    assert result == ["a", "b", "d", "e"]


def test_list_knockout_multiple_items():
    """Multiple knockouts in one merge."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b", "c", "d"], ["--a", "--c", "e"])
    assert result == ["b", "d", "e"]


def test_list_knockout_ruby_doc_example():
    """Mirror the canonical example from the Ruby deep_merge docs."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["1", "2"], ["--1", "3"])
    assert result == ["2", "3"]


def test_list_knockout_overrides_extend_existing_list():
    """Knockouts force filter+append semantics regardless of extend_existing_list."""
    merg = DeepMerge(knockout_prefix="--", extend_existing_list=True)
    result = merg.merge(["a", "b"], ["--a", "c"])
    assert result == ["b", "c"]


def test_list_knockout_overrides_overwrite_list():
    """Knockouts force filter+append semantics regardless of overwrite_list."""
    merg = DeepMerge(knockout_prefix="--", overwrite_list=True)
    result = merg.merge(["a", "b", "c"], ["--a", "d"])
    # Without knockouts, overwrite_list would give ['--a', 'd'] -> stripped ['d']
    # With knockouts, we filter target by knockouts and append non-knockouts
    assert result == ["b", "c", "d"]


def test_list_knockout_disabled_when_prefix_empty():
    """Empty prefix means no knockout behavior — '--a' is a literal string."""
    merg = DeepMerge()  # default knockout_prefix=""
    result = merg.merge(["a", "b"], ["--a", "c"])
    # '--a' is treated as a normal string and overwrites target[0]
    assert "--a" in result


# -----------------------------------------------------------------------------
# Dict knockout
# -----------------------------------------------------------------------------

def test_dict_value_knockout_to_none():
    """Source value equals prefix exactly -> set key to knockout_value (default None)."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"a": "--"})
    assert result == {"a": None, "b": 2}


def test_dict_value_knockout_custom_value():
    """knockout_value applies in dict context too."""
    merg = DeepMerge(knockout_prefix="--", knockout_value="GONE")
    result = merg.merge({"a": 1, "b": 2}, {"a": "--"})
    assert result == {"a": "GONE", "b": 2}


def test_dict_knockout_does_not_affect_non_matching_keys():
    """Other keys merge normally."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"a": "--", "b": 99})
    assert result == {"a": None, "b": 99}


def test_dict_knockout_against_missing_key_is_noop():
    """Knockout for a key that doesn't exist in target -> key is skipped entirely."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"b": 2}, {"a": "--"})
    # No 'a' in target, so knockout has nothing to remove; result is just target.
    assert result == {"b": 2}


def test_dict_knockout_only_matches_exact_prefix():
    """A value that contains the prefix but isn't equal to it is not knocked out."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": "old"}, {"a": "--something"})
    # '--something' is not equal to '--', so it's a normal string overwrite
    assert result == {"a": "--something"}


# -----------------------------------------------------------------------------
# Dict key knockout (prefix on the key itself removes the key from target)
# -----------------------------------------------------------------------------

def test_dict_key_knockout_removes_key():
    """Source key '--a' removes key 'a' from target."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"--a": ""})
    assert result == {"b": 2}


def test_dict_key_knockout_missing_key_is_noop():
    """Knockout key for a missing target key is a no-op."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"b": 2}, {"--a": ""})
    assert result == {"b": 2}


def test_dict_key_knockout_value_is_ignored():
    """Whatever value sits under a knockout key is discarded."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"--a": "anything"})
    assert result == {"b": 2}


def test_dict_key_knockout_hiera_example():
    """Mirror the Hiera-style example: {'--key_to_remove': ''}."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"key_to_remove": "old", "keep": "me"},
        {"--key_to_remove": ""},
    )
    assert result == {"keep": "me"}


def test_dict_key_knockout_then_readd_same_key():
    """'--a' strips target's 'a', and a subsequent 'a' in source adds the new value."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": "old"}, {"--a": "", "a": "new"})
    assert result == {"a": "new"}


def test_dict_key_knockout_prefix_alone_is_literal_key():
    """The prefix by itself is not a knockout key — it's a literal key '--'."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1}, {"--": "literal"})
    assert result == {"a": 1, "--": "literal"}


def test_dict_key_knockout_non_string_key_ignored():
    """Non-string keys can't carry the prefix — they merge normally."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({1: "one", 2: "two"}, {1: "ONE"})
    assert result == {1: "ONE", 2: "two"}


def test_dict_key_knockout_disabled_when_prefix_empty():
    """Empty prefix means '--a' is a literal key, not a knockout."""
    merg = DeepMerge()
    result = merg.merge({"a": 1}, {"--a": "x"})
    assert result == {"a": 1, "--a": "x"}


def test_dict_key_knockout_respects_exclude_paths():
    """exclude_paths blocks both mutation and key-level knockout."""
    merg = DeepMerge(knockout_prefix="--", exclude_paths=["a"])
    result = merg.merge({"a": 1, "b": 2}, {"--a": ""})
    assert result == {"a": 1, "b": 2}


def test_dict_key_knockout_custom_prefix():
    """Key knockout works with any prefix string."""
    merg = DeepMerge(knockout_prefix="DEL:")
    result = merg.merge({"a": 1, "b": 2}, {"DEL:a": ""})
    assert result == {"b": 2}


# -----------------------------------------------------------------------------
# Nested knockout
# -----------------------------------------------------------------------------

def test_nested_dict_knockout():
    """Knockout works inside nested dicts."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"outer": {"inner": "keep_me", "other": 1}},
        {"outer": {"inner": "--"}},
    )
    assert result == {"outer": {"inner": None, "other": 1}}


def test_nested_list_knockout():
    """Knockout works inside nested lists."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"items": ["a", "b", "c"]},
        {"items": ["--b", "d"]},
    )
    assert result == {"items": ["a", "c", "d"]}


# -----------------------------------------------------------------------------
# Custom prefix
# -----------------------------------------------------------------------------

def test_custom_knockout_prefix():
    """Knockout prefix can be any string."""
    merg = DeepMerge(knockout_prefix="DEL:")
    result = merg.merge(["a", "b", "c"], ["DEL:b"])
    assert result == ["a", "c"]


# -----------------------------------------------------------------------------
# knockout_value type validation
# -----------------------------------------------------------------------------

def test_knockout_value_set_rejected():
    """A set knockout_value violates the strict-types contract -> reject at init."""
    with pytest.raises(InvalidTypeError):
        DeepMerge(knockout_prefix="--", knockout_value={1, 2})


def test_knockout_value_tuple_rejected():
    """A tuple knockout_value is not in ALLOWED_TYPES -> reject."""
    with pytest.raises(InvalidTypeError):
        DeepMerge(knockout_prefix="--", knockout_value=(1, 2))


def test_knockout_value_custom_object_rejected():
    """Arbitrary custom objects are not allowed."""
    class Foo:
        pass
    with pytest.raises(InvalidTypeError):
        DeepMerge(knockout_prefix="--", knockout_value=Foo())


def test_knockout_value_valid_types_accepted():
    """All ALLOWED_TYPES are valid knockout_value choices."""
    # None (default), str, int, float, bool, list, dict, and explicit None
    for v in [None, "str", 0, 1.5, True, False, [], [1, 2], {}, {"k": "v"}]:
        DeepMerge(knockout_prefix="--", knockout_value=v)  # should not raise
