import pytest

from merg import DeepMerge, InvalidTypeError

# -----------------------------------------------------------------------------
# Document root must be dict or list
# -----------------------------------------------------------------------------

def test_top_level_root_must_be_dict_or_list():
    """Scalar/set/None roots raise — unrelated to knockout, which only exists
    at keys and list items."""
    merg = DeepMerge(knockout_prefix="--")
    with pytest.raises(InvalidTypeError):
        merg.merge(5, {"a": 1})
    with pytest.raises(InvalidTypeError):
        merg.merge({"a": 1}, 5)
    with pytest.raises(InvalidTypeError):
        merg.merge([1, 2, 3], "--")
    with pytest.raises(InvalidTypeError):
        merg.merge(None, {})


def test_top_level_container_roots_are_valid():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({}, {"a": 1}) == {"a": 1}
    assert merg.merge([], ["a"]) == ["a"]


# -----------------------------------------------------------------------------
# knockout_value option is deleted
# -----------------------------------------------------------------------------

def test_knockout_value_option_is_deleted():
    """No deprecation shim (S3): knockout_value fails as an unknown option."""
    with pytest.raises(TypeError, match="unknown option"):
        DeepMerge(knockout_value=10)
    with pytest.raises(TypeError, match="unknown option"):
        DeepMerge(knockout_prefix="--", knockout_value="REMOVED")


# -----------------------------------------------------------------------------
# A bare prefix is data — one removal form only
# -----------------------------------------------------------------------------

def test_bare_marker_at_dict_value_is_data():
    """{'a': '--'} assigns the two-character string; it does not remove or null."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": 5}, {"a": "--"}) == {"a": "--"}
    assert merg.merge({"a": 1, "b": 2}, {"a": "--", "b": 99}) == {"a": "--", "b": 99}


def test_bare_marker_assigns_at_missing_key():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({}, {"a": "--"}) == {"a": "--"}
    assert merg.merge({"b": 2}, {"a": "--"}) == {"a": "--", "b": 2}


def test_bare_marker_nested_is_data():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"outer": {"inner": "keep_me", "other": 1}},
        {"outer": {"inner": "--"}},
    )
    assert result == {"outer": {"inner": "--", "other": 1}}


def test_bare_marker_in_list_is_ordinary_item():
    """Bug 3, resolved the other way: a bare marker surviving as a literal
    is now the correct behavior."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([1, 2, 3], ["--"]) == ["--", 2, 3]
    assert merg.merge([], ["--", "a"]) == ["--", "a"]


def test_bare_marker_alongside_payload_in_list():
    """'--b' removes b; '--' stays as data."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge(["a", "b"], ["--", "--b"]) == ["a", "--"]


def test_bare_marker_prefix_alone_is_literal_key():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1}, {"--": "y"})
    assert result == {"a": 1, "--": "y"}


def test_prefixed_value_that_addresses_nothing_is_data():
    """'--something' at a dict value is an ordinary string."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": "old"}, {"a": "--something"}) == {"a": "--something"}


def test_bare_marker_without_prefix_option_is_just_a_string():
    merg = DeepMerge()
    assert merg.merge({"a": 1}, {"a": "--"}) == {"a": "--"}


# -----------------------------------------------------------------------------
# Payload form on dict keys — removes the named key, value ignored
# -----------------------------------------------------------------------------

def test_dict_key_knockout_removes_key():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"--a": ""})
    assert result == {"b": 2}


def test_dict_key_knockout_value_is_ignored():
    """The value under a knockout key is never inspected — any type works."""
    merg = DeepMerge(knockout_prefix="--")
    for value in ["anything", "", None, 0, {"deep": 1}, [1, 2]]:
        assert merg.merge({"a": 1, "b": 2}, {"--a": value}) == {"b": 2}


def test_dict_key_knockout_missing_key_is_noop():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"b": 2}, {"--a": ""})
    assert result == {"b": 2}


def test_dict_key_knockout_then_readd_same_key():
    """Replace idiom: remove then re-add in one patch, instead of deep-merging."""
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": {"x": 1}}, {"--a": "", "a": {"y": 2}})
    assert result == {"a": {"y": 2}}


def test_dict_key_knockout_non_string_key_ignored():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({1: "one", 2: "two"}, {1: "ONE"})
    assert result == {1: "ONE", 2: "two"}


def test_dict_key_knockout_disabled_when_prefix_empty():
    merg = DeepMerge()
    result = merg.merge({"a": 1}, {"--a": "x"})
    assert result == {"a": 1, "--a": "x"}


def test_dict_key_knockout_and_exclude_paths():
    """'a' and '--a' are different patch keys. Excluding 'a' drops a patch
    entry spelled 'a' but cannot touch a '--a' knockout instruction —
    blocking both removal spellings means excluding both spellings."""
    base = {"a": 9, "b": 2}

    merg = DeepMerge(knockout_prefix="--", exclude_paths=["a"])
    assert merg.merge(base, {"--a": ""}) == {"b": 2}

    merg = DeepMerge(knockout_prefix="--", exclude_paths=["--a"])
    assert merg.merge(base, {"--a": ""}) == {"a": 9, "b": 2}


def test_dict_key_knockout_custom_prefix():
    merg = DeepMerge(knockout_prefix="DEL:")
    result = merg.merge({"a": 1, "b": 2}, {"DEL:a": ""})
    assert result == {"b": 2}


# -----------------------------------------------------------------------------
# Payload form on list items — removes by value, all occurrences
# -----------------------------------------------------------------------------

def test_list_knockout_removes_matching_target_item():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["one", "two", "three"], ["--one", "four"])
    assert result == ["two", "three", "four"]


def test_list_knockout_removes_all_occurrences():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "a", "b"], ["--a"])
    assert result == ["b"]


def test_list_knockout_no_match_is_safe():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b"], ["--zzz"])
    assert result == ["a", "b"]


def test_list_knockout_preserves_target_order():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b", "c", "d"], ["--c", "e"])
    assert result == ["a", "b", "d", "e"]


def test_list_knockout_multiple_items():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b", "c", "d"], ["--a", "--c", "e"])
    assert result == ["b", "d", "e"]


def test_list_knockout_matches_string_values_only():
    """A string-prefix scheme cannot address non-string values."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([80, 443], ["--443"]) == [80, 443]


def test_list_knockout_ruby_doc_example():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["1", "2"], ["--1", "3"])
    assert result == ["2", "3"]


def test_list_knockout_overrides_extend_existing_list():
    merg = DeepMerge(knockout_prefix="--", extend_existing_list=True)
    result = merg.merge(["a", "b"], ["--a", "c"])
    assert result == ["b", "c"]


def test_list_knockout_overrides_overwrite_list():
    merg = DeepMerge(knockout_prefix="--", overwrite_list=True)
    result = merg.merge(["a", "b", "c"], ["--a", "d"])
    assert result == ["b", "c", "d"]


def test_nested_list_knockout():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"items": ["a", "b", "c"]},
        {"items": ["--b", "d"]},
    )
    assert result == {"items": ["a", "c", "d"]}


def test_custom_knockout_prefix():
    merg = DeepMerge(knockout_prefix="DEL:")
    result = merg.merge(["a", "b", "c"], ["DEL:b"])
    assert result == ["a", "c"]
