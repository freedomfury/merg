import yaml
import sys

# Custom dumper to avoid aliases
class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

try:
    with open('test_data.yml', 'r') as f:
        data = yaml.safe_load(f)

    with open('test_data.yml', 'w') as f:
        yaml.dump(data, f, Dumper=NoAliasDumper, default_flow_style=False, sort_keys=False)
    print("Successfully flattened test_data.yml")
except Exception as e:
    print(f"Error flattening YAML: {e}")
    sys.exit(1)
