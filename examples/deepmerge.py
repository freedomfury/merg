# examples/deepmerge.py
import yaml
from deep_merge import DeepMerge

source = {
    "server": {
        "port": 8080,
        "host": "localhost",
        "tags": ["dev"]
    }
}

target = {
    "server": {
        "port": 80,
        "tags": ["base", "http"]
    },
    "database": "postgres"
}

# Example 1: Default Merge (Overwrite list)
print("--- Example 1: Default Merge ---")
merger = DeepMerge()
result = merger.merge(target, source)
print(yaml.dump(result, sort_keys=False))

# Example 2: Extend List
print("\n--- Example 2: Extend List (Interleave) ---")
merger = DeepMerge(extend_existing_list=True)
result = merger.merge(target, source)
print(yaml.dump(result, sort_keys=False))

# --- Real World Scenarios ---

def print_scenario(title, data):
    print(f"\n--- {title} ---")
    print(yaml.dump(data, sort_keys=False))

# Scenario 3: Configuration Management
def scenario_config_merge():
    default_config = {
        "app": {
            "name": "MyParser",
            "debug": False,
            "timeout": 30,
            "logging": {
                "level": "INFO",
                "file": "/var/log/app.log"
            }
        },
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }

    user_config = {
        "app": {
            "debug": True,
            "logging": {"level": "DEBUG"}
        },
        "database": {"host": "db.prod.internal"}
    }

    merger = DeepMerge()
    merged = merger.merge(default_config, user_config)
    print_scenario("Scenario 3: Config Merging (Defaults + Overrides)", merged)

# Scenario 4: Permission Aggregation
def scenario_permissions_merge():
    base_role = {
        "role": "editor",
        "permissions": ["read", "write"]
    }
    admin_overlay = {
        "role": "admin",
        "permissions": ["delete", "audit"]
    }

    # Extend + Deduplicate
    merger = DeepMerge(extend_existing_list=True, deduplicate_list=True)
    merged = merger.merge(base_role, admin_overlay)
    print_scenario("Scenario 4: Permission Aggregation (Extend + Dedupe)", merged)

# Scenario 5: Secure Merge (Exclusion)
def scenario_secure_merge():
    current_user = {
        "username": "jdoe",
        "internal": {"is_admin": False}
    }
    update_payload = {
        "username": "jdoe_updated",
        "internal": {"is_admin": True} # Malicious attempt
    }

    merger = DeepMerge(exclude_paths=["internal"])
    merged = merger.merge(current_user, update_payload)
    print_scenario("Scenario 5: Secure Merge (Excluding 'internal')", merged)

if __name__ == "__main__":
    # The first two examples run on import if we don't guard them, 
    # but for this simple script it's fine.
    scenario_config_merge()
    scenario_permissions_merge()
    scenario_secure_merge()
