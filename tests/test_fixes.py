from merg import DeepMerge

def test_deep_copy_behavior():
    """Verify that merged result does not reference original mutable objects."""
    target = {"a": {"x": 1}, "b": [1, 2]}
    source = {"c": 3}
    
    merger = DeepMerge()
    result = merger.merge(target, source)
    
    # Modify result
    result["a"]["x"] = 999
    result["b"].append(3)
    
    # Verify originals are unchanged
    assert target["a"]["x"] == 1
    assert len(target["b"]) == 2
    
def test_deep_copy_source_references():
    """Verify that source mutable objects are copied, not referenced."""
    target = {}
    source_list = [1, 2]
    source = {"a": source_list}
    
    merger = DeepMerge()
    result = merger.merge(target, source)
    
    # Modify result
    result["a"].append(3)
    
    # Verify source is unchanged
    assert len(source_list) == 2

def test_dot_key_exclusion():
    """Verify exclusion of keys containing dots using tuple paths."""
    target = {
        "k8s.io": {"name": "old"},
        "simple": "keep"
    }
    source = {
        "k8s.io": {"name": "new"},
        "simple": "update"
    }
    
    # Exclude "k8s.io" -> "name"
    merger = DeepMerge(exclude_paths=[("k8s.io", "name")])
    result = merger.merge(target, source)
    
    assert result["k8s.io"]["name"] == "old"
    assert result["simple"] == "update"

def test_legacy_dot_notation_exclusion():
    """Verify legacy string dot notation still works."""
    target = {"a": {"b": 1}}
    source = {"a": {"b": 2}}

    merger = DeepMerge(exclude_paths=["a.b"])
    result = merger.merge(target, source)

    assert result["a"]["b"] == 1


# Bug #10: preserve_mismatch in a list path was appending the target item
# directly without deepcopy, leaking a reference to the caller's data.
def test_preserve_mismatch_top_level_list_does_not_leak_reference():
    target = [{"nested": "original"}]
    source = ["replaced_with_string"]
    merger = DeepMerge(preserve_mismatch=True)
    result = merger.merge(target, source)

    # Mutate the result; target must remain untouched.
    result[0]["nested"] = "MUTATED"

    assert target[0]["nested"] == "original"
    assert result[0] is not target[0]


def test_preserve_mismatch_nested_list_does_not_leak_reference():
    target = {"items": [{"nested": "original"}]}
    source = {"items": ["replaced_with_string"]}
    merger = DeepMerge(preserve_mismatch=True)
    result = merger.merge(target, source)

    result["items"][0]["nested"] = "MUTATED"

    assert target["items"][0]["nested"] == "original"
    assert result["items"][0] is not target["items"][0]
