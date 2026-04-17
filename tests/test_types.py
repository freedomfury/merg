import pytest
from deep_merge import DeepMerge, InvalidTypeError

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
