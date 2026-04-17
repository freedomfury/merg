import pytest
import copy
from deep_merge import DeepMerge

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
