import pytest
import yaml
from pathlib import Path
from merg import DeepMerge

def get_test_cases():
    root = Path(__file__).parent
    with open(root / "test_data.yml", "r") as f:
        data = yaml.safe_load(f)
    return [(case_id, data[case_id]) for case_id in data if case_id.startswith("uc")]

@pytest.mark.parametrize("case_id, case_data", get_test_cases())
def test_deep_merge_yaml_cases(case_id, case_data):
    options = case_data.get("option", {})
    source = case_data.get("source")
    target = case_data.get("target")
    expected = case_data.get("answer")

    merger = DeepMerge(**options)
    result = merger.merge(target, source)
    
    assert result == expected, f"Failed {case_id}: expected {expected}, got {result}"
