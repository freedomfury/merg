import pytest

from merg import DeepMerge, InvalidTypeError

# -----------------------------------------------------------------------------
# Document root must be dict or list (new rule)
# -----------------------------------------------------------------------------

def test_top_level_root_must_be_dict_or_list():
    """Scalar/set/None roots raise; this makes a top-level knockout unreachable."""
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
# Bare marker in dicts — removes the key at its address
# -----------------------------------------------------------------------------

def test_dict_bare_marker_removes_key():
    """{'a': 5} + {'a': '--'} -> {} — key removed, not nulled."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": 5}, {"a": "--"}) == {}


def test_dict_bare_marker_removes_only_that_key():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": 5, "b": 1}, {"a": "--"}) == {"b": 1}


def test_dict_bare_marker_does_not_affect_other_keys():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": 1, "b": 2}, {"a": "--", "b": 99}) == {"b": 99}


def test_dict_bare_marker_missing_key_is_noop():
    """Nothing to remove — the key is not created."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({}, {"a": "--"}) == {}
    assert merg.merge({"b": 2}, {"a": "--"}) == {"b": 2}


def test_dict_bare_marker_nested_no_cascade():
    """Removing the last key of a nested dict leaves an empty dict — no cascade."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": {"b": 1}}, {"a": {"b": "--"}}) == {"a": {}}


def test_nested_dict_bare_marker_removes_nested_key():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"outer": {"inner": "keep_me", "other": 1}},
        {"outer": {"inner": "--"}},
    )
    assert result == {"outer": {"other": 1}}


def test_dict_bare_marker_only_matches_exact_prefix():
    """A value containing the prefix but not equal to it is normal data."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": "old"}, {"a": "--something"}) == {"a": "--something"}


# -----------------------------------------------------------------------------
# Dict payload form (--key) — removes by key name, unchanged semantics
# -----------------------------------------------------------------------------

def test_dict_key_knockout_removes_key():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"--a": ""})
    assert result == {"b": 2}


def test_dict_key_knockout_missing_key_is_noop():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"b": 2}, {"--a": ""})
    assert result == {"b": 2}


def test_dict_key_knockout_value_is_ignored():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1, "b": 2}, {"--a": "anything"})
    assert result == {"b": 2}


def test_dict_key_knockout_hiera_example():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(
        {"key_to_remove": "old", "keep": "me"},
        {"--key_to_remove": ""},
    )
    assert result == {"keep": "me"}


def test_dict_key_knockout_then_readd_same_key():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": "old"}, {"--a": "", "a": "new"})
    assert result == {"a": "new"}


def test_dict_key_knockout_prefix_alone_is_literal_key():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": 1}, {"--": "literal"})
    assert result == {"a": 1, "--": "literal"}


def test_dict_key_knockout_non_string_key_ignored():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({1: "one", 2: "two"}, {1: "ONE"})
    assert result == {1: "ONE", 2: "two"}


def test_dict_key_knockout_disabled_when_prefix_empty():
    merg = DeepMerge()
    result = merg.merge({"a": 1}, {"--a": "x"})
    assert result == {"a": 1, "--a": "x"}


def test_dict_key_knockout_respects_exclude_paths():
    merg = DeepMerge(knockout_prefix="--", exclude_paths=["a"])
    result = merg.merge({"a": 1, "b": 2}, {"--a": ""})
    assert result == {"a": 1, "b": 2}


def test_dict_bare_marker_respects_exclude_paths():
    """A protected path can neither be overwritten nor removed."""
    merg = DeepMerge(knockout_prefix="--", exclude_paths=["a"])
    result = merg.merge({"a": 1, "b": 2}, {"a": "--"})
    assert result == {"a": 1, "b": 2}


def test_dict_key_knockout_custom_prefix():
    merg = DeepMerge(knockout_prefix="DEL:")
    result = merg.merge({"a": 1, "b": 2}, {"DEL:a": ""})
    assert result == {"b": 2}


# -----------------------------------------------------------------------------
# Bare marker in lists — wipes the target list; position irrelevant
# -----------------------------------------------------------------------------

def test_list_bare_marker_wipes_target():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([1, 2, 3], ["--"]) == []


def test_list_bare_marker_wipe_then_appends():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([1, 2, 3], ["--", "9"]) == ["9"]


def test_list_bare_marker_position_irrelevant():
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([1, 2, 3], ["9", "--"]) == ["9"]


def test_list_bare_marker_empty_target_appends_rest():
    """Bug 3: the marker never survives into output as a literal string."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge([], ["--", "a"]) == ["a"]


def test_list_bare_and_payload_markers_together():
    """Bug 3: wipe wins; payload knockout finds nothing left, appends nothing."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge(["a", "b"], ["--", "--b"]) == []


# -----------------------------------------------------------------------------
# List payload form (--item) — removes by value, unchanged semantics
# -----------------------------------------------------------------------------

def test_list_knockout_removes_matching_target_item():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["one", "two", "three"], ["--one", "four"])
    assert result == ["two", "three", "four"]


def test_list_knockout_strips_only_knockout_entries():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["a", "b"], ["--a"])
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


def test_list_knockout_disabled_when_prefix_empty():
    merg = DeepMerge()
    result = merg.merge(["a", "b"], ["--a", "c"])
    assert "--a" in result


def test_list_payload_knockout_removes_by_value_wherever_it_sits():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge(["nginx", "curl", "git"], ["--curl"])
    assert result == ["nginx", "git"]


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


# -----------------------------------------------------------------------------
# Tokens are never data — consumption in source-only subtrees
# -----------------------------------------------------------------------------

def test_tokens_in_new_subtrees_are_consumed():
    """A source-only subtree passes through the merge machinery so its
    markers are interpreted (as no-ops against an empty target), not copied."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({}, {"x": {"b": "--"}}) == {"x": {}}
    assert merg.merge({}, {"items": ["--", "a"]}) == {"items": ["a"]}


def test_result_contains_no_marker_strings():
    merg = DeepMerge(knockout_prefix="--")
    result = merg.merge({"a": [1]}, {"b": {"c": "--"}, "d": ["--", "x"]})
    assert result == {"a": [1], "b": {}, "d": ["x"]}


def test_mismatch_branch_consumes_markers():
    """Finding 1: a source subtree adopted via the type-mismatch branch must
    still pass through the machinery — bare markers are consumed, not copied."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": 5}, {"a": ["--"]}) == {"a": []}
    assert merg.merge({"a": 5}, {"a": ["--", "k"]}) == {"a": ["k"]}
    assert merg.merge({"a": 5}, {"a": {"b": "--"}}) == {"a": {}}
    assert merg.merge(["x"], [["--"]]) == [[]]


def _assert_no_markers(node, prefix="--"):
    """Walk a result tree; no string may start with the knockout prefix.
    (Target data in these tests is marker-free by construction.)"""
    if isinstance(node, str):
        assert not node.startswith(prefix), f"marker leaked into result: {node!r}"
    elif isinstance(node, dict):
        for v in node.values():
            _assert_no_markers(v, prefix)
    elif isinstance(node, list):
        for item in node:
            _assert_no_markers(item, prefix)


def test_markers_never_leak_through_any_adoption_path():
    """Generic sweep: every path that adopts source data — new dict keys,
    source-only list items, and the type-mismatch branch — consumes markers.
    Walks the whole result instead of asserting specific values."""
    merg = DeepMerge(knockout_prefix="--")
    cases = [
        ({}, {"x": {"b": "--"}}),
        ([], ["--", "a"]),
        ({"a": [1]}, {"b": {"c": "--"}, "d": ["--", "x"]}),
        ({"a": 5}, {"a": ["--"]}),
        ({"a": 5}, {"a": {"b": "--"}}),
        ({"a": 1}, {"a": {"b": ["--", "k"]}}),
        (["x"], [["--"]]),
        ({"a": "scalar"}, {"a": {"deep": {"deeper": ["--"]}}}),
    ]
    for target, source in cases:
        _assert_no_markers(merg.merge(target, source))


def test_target_side_marker_is_data():
    """Only source is interpreted: a marker already in target data is literal."""
    merg = DeepMerge(knockout_prefix="--")
    assert merg.merge({"a": "--", "b": 1}, {}) == {"a": "--", "b": 1}
