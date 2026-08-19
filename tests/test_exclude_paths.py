from merg import DeepMerge

# -----------------------------------------------------------------------------
# exclude_paths filters the patch: the named paths are removed from the source
# before merging, and whatever remains merges by the ordinary rules. A dropped
# value is never inspected; there is no target-side behavior.
# -----------------------------------------------------------------------------

def test_excluded_key_dropped_whatever_the_value():
    """The patch value under an excluded path is dropped unseen — scalar, dict,
    list, None, or a bare knockout marker all leave the base untouched."""
    base = {"a": "kept", "b": 1}
    for patch in [
        {"a": "new", "b": 2},
        {"a": {"deep": 1}, "b": 2},
        {"a": [1, 2], "b": 2},
        {"a": None, "b": 2},
    ]:
        merger = DeepMerge(exclude_paths=["a"])
        assert merger.merge(base, patch) == {"a": "kept", "b": 2}

    merger = DeepMerge(knockout_prefix="--", exclude_paths=["a"])
    assert merger.merge(base, {"a": "--", "b": 2}) == {"a": "kept", "b": 2}


def test_excluding_absent_path_is_a_noop():
    merger = DeepMerge(exclude_paths=[("items", 5), "missing.key"])
    result = merger.merge({"items": ["t0"]}, {"items": ["s0"]})
    assert result == {"items": ["s0"]}


def test_patch_is_not_mutated_by_exclusion():
    patch = {"a": {"deep": 1}, "c": 2}
    merger = DeepMerge(exclude_paths=["a.deep"])
    merger.merge({"a": {"x": 1}}, patch)
    assert patch == {"a": {"deep": 1}, "c": 2}


def test_excluding_a_key_does_not_create_it():
    merger = DeepMerge(exclude_paths=["a"])
    assert merger.merge({}, {"a": 1, "b": 2}) == {"b": 2}


# -----------------------------------------------------------------------------
# List indices — dropping an element shifts the ones after it
# -----------------------------------------------------------------------------

def test_exclude_path_in_default_list_merge():
    """Excluding patch index 0 drops s0; the remaining patch items line up
    one slot earlier, so s1 lands at index 0."""
    merger = DeepMerge(exclude_paths=[("items", 0)])
    result = merger.merge(
        {"items": ["t0", "t1"]},
        {"items": ["s0", "s1"]},
    )
    assert result == {"items": ["s1", "t1"]}


def test_exclude_path_full_list_default_mode():
    """Excluding patch index 1: s0 and s2 shift forward one slot each."""
    merger = DeepMerge(exclude_paths=[("items", 1)])
    result = merger.merge(
        {"items": ["t0", "t1", "t2"]},
        {"items": ["s0", "s1", "s2"]},
    )
    assert result == {"items": ["s0", "s2", "t2"]}


def test_exclude_path_in_extend_existing_list_mode():
    """Extend mode: the dropped s0 never appears; remaining patch extends."""
    merger = DeepMerge(exclude_paths=[("items", 0)], extend_existing_list=True)
    result = merger.merge(
        {"items": ["t0", "t1"]},
        {"items": ["s0", "s1"]},
    )
    assert result == {"items": ["s1", "t0", "t1"]}


def test_exclude_path_for_source_item_beyond_target_length():
    """A patch item beyond target length is still a patch item — excluded,
    it is simply dropped."""
    merger = DeepMerge(exclude_paths=[("items", 1)])
    result = merger.merge(
        {"items": ["t0"]},
        {"items": ["s0", "s1"]},
    )
    assert result == {"items": ["s0"]}


def test_exclude_path_target_only_items_are_untouched():
    """Exclusion only reads the patch; target-only items are out of reach."""
    merger = DeepMerge(exclude_paths=[("items", 2)])
    result = merger.merge(
        {"items": ["t0", "t1", "t2"]},
        {"items": ["s0"]},
    )
    assert result == {"items": ["s0", "t1", "t2"]}


# -----------------------------------------------------------------------------
# Bug 2 — exclusion now applies in knockout list mode
# -----------------------------------------------------------------------------

def test_bug2_exclusion_applies_in_knockout_list_mode():
    """With list knockouts present, excluding patch index 0 vs index 1 now
    produces different results (previously exclude_paths was ignored)."""
    base = {"items": ["t0", "t1"]}
    patch = {"items": ["--t0", "s1"]}

    # '--t0' is dropped from the patch: no knockout fires, and the remaining
    # 's1' shifts to index 0, overwriting t0 positionally.
    merger = DeepMerge(knockout_prefix="--", exclude_paths=[("items", 0)])
    assert merger.merge(base, patch) == {"items": ["s1", "t1"]}

    # 's1' is dropped instead: the knockout fires, nothing is left to append.
    merger = DeepMerge(knockout_prefix="--", exclude_paths=[("items", 1)])
    assert merger.merge(base, patch) == {"items": ["t1"]}
