from merg import DeepMerge


# -----------------------------------------------------------------------------
# Bug #2 / #3 — exclude_paths must apply to list items in *all* merge modes
# (default index merge, extend_existing_list, and source-only items beyond
# target length).
# -----------------------------------------------------------------------------

def test_exclude_path_in_default_list_merge():
    """Baseline: exclude index 0 in default (index-overwrite) mode."""
    merger = DeepMerge(exclude_paths=[("items", 0)])
    result = merger.merge(
        {"items": ["t0", "t1"]},
        {"items": ["s0", "s1"]},
    )
    # source[0] excluded -> target[0] preserved; source[1] wins at index 1
    assert result == {"items": ["t0", "s1"]}


def test_exclude_path_in_extend_existing_list_mode():
    """Bug #2: extend mode currently bypasses exclude_paths for list items."""
    merger = DeepMerge(exclude_paths=[("items", 0)], extend_existing_list=True)
    result = merger.merge(
        {"items": ["t0", "t1"]},
        {"items": ["s0", "s1"]},
    )
    # Without exclusion, extend would give ['s0', 't0', 's1', 't1'].
    # With exclusion of source index 0, 's0' must NOT appear.
    assert "s0" not in result["items"]


def test_exclude_path_for_source_item_beyond_target_length():
    """Bug #3: source-only items beyond target length currently bypass exclude_paths."""
    merger = DeepMerge(exclude_paths=[("items", 1)])
    result = merger.merge(
        {"items": ["t0"]},
        {"items": ["s0", "s1"]},
    )
    # source has indices 0 and 1. Index 1 is beyond target length and excluded.
    # Expected: index 0 merges normally (s0 wins), index 1 is excluded -> dropped.
    assert "s1" not in result["items"]


def test_exclude_path_does_not_drop_target_only_items():
    """Target-only items (no source counterpart) are preserved regardless of exclusion.

    Mirrors dict exclusion semantics: exclude_paths controls what *source*
    can write; target data is always preserved unless source overrides it.
    """
    merger = DeepMerge(exclude_paths=[("items", 2)])
    result = merger.merge(
        {"items": ["t0", "t1", "t2"]},
        {"items": ["s0"]},
    )
    # Target index 2 has no source counterpart, so exclusion is a no-op for it.
    assert "t2" in result["items"]
    # And source[0] still wins at index 0 (not excluded).
    assert "s0" in result["items"]


def test_exclude_path_full_list_default_mode():
    """Concrete: exclude index 1 in default mode preserves target[1]."""
    merger = DeepMerge(exclude_paths=[("items", 1)])
    result = merger.merge(
        {"items": ["t0", "t1", "t2"]},
        {"items": ["s0", "s1", "s2"]},
    )
    # Index 0: source wins. Index 1: excluded -> target wins. Index 2: source wins.
    assert result == {"items": ["s0", "t1", "s2"]}
