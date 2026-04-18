from merg import DeepMerge


# Bug #9: overwrite_list=True returns early, silently skipping
# deduplicate_list and sort_merged_list post-processing.

def test_overwrite_list_with_deduplicate_list():
    """overwrite_list=True must still apply deduplicate_list."""
    merger = DeepMerge(overwrite_list=True, deduplicate_list=True)
    result = merger.merge([], [1, 1, 2, 2, 3])
    assert result == [1, 2, 3]


def test_overwrite_list_with_sort_merged_list():
    """overwrite_list=True must still apply sort_merged_list."""
    merger = DeepMerge(overwrite_list=True, sort_merged_list=True)
    result = merger.merge([], [3, 1, 2])
    assert result == [1, 2, 3]


def test_overwrite_list_with_both_dedup_and_sort():
    """overwrite_list=True with both options."""
    merger = DeepMerge(overwrite_list=True, deduplicate_list=True, sort_merged_list=True)
    result = merger.merge([], [3, 1, 2, 1, 3])
    assert result == [1, 2, 3]


def test_deduplicate_list_with_unhashable_items():
    """Dicts aren't hashable, so dict.fromkeys raises and the O(n^2) fallback runs."""
    merger = DeepMerge(overwrite_list=True, deduplicate_list=True)
    result = merger.merge([], [{"a": 1}, {"a": 1}, {"b": 2}])
    assert result == [{"a": 1}, {"b": 2}]


def test_sort_merged_list_with_uncomparable_items():
    """Mixed-type lists can't be sorted in Py3; the TypeError is swallowed."""
    merger = DeepMerge(overwrite_list=True, sort_merged_list=True)
    result = merger.merge([], [1, "a", 2])
    assert result == [1, "a", 2]
