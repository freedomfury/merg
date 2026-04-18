import pytest
from merg import DeepMerge


# Bug #6: Unknown option names were silently accepted, masking typos like
# `extend_exsting_list=True`. Reject unknown options at __init__.

def test_unknown_option_raises_typeerror():
    with pytest.raises(TypeError, match="unknown option"):
        DeepMerge(extend_exsting_list=True)  # typo


def test_unknown_option_lists_all_unknowns():
    """Multiple unknowns should all be reported."""
    with pytest.raises(TypeError) as exc_info:
        DeepMerge(foo=1, bar=2)
    msg = str(exc_info.value)
    assert "foo" in msg
    assert "bar" in msg


def test_all_known_options_still_accepted():
    """Sanity check: every documented option is allowed."""
    DeepMerge(
        preserve_mismatch=True,
        exclude_paths=[],
        overwrite_list=True,
        extend_existing_list=False,
        deduplicate_list=False,
        sort_merged_list=False,
        merge_none_value=False,
        knockout_prefix="--",
        knockout_value=None,
    )


# Bug #7: exclude_paths=None crashed with cryptic 'NoneType is not iterable'.
def test_exclude_paths_none_raises_clear_error():
    with pytest.raises((TypeError, ValueError), match="exclude_paths"):
        DeepMerge(exclude_paths=None)


# Bug #8: exclude_paths=[None] (or any non-string non-iterable) crashed cryptically.
def test_exclude_paths_with_none_entry_raises_clear_error():
    with pytest.raises((TypeError, ValueError), match="exclude_paths"):
        DeepMerge(exclude_paths=[None])


def test_exclude_paths_with_int_entry_raises_clear_error():
    """An int isn't a string or a path tuple — should fail clearly."""
    with pytest.raises((TypeError, ValueError), match="exclude_paths"):
        DeepMerge(exclude_paths=[42])
