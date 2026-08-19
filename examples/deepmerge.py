# examples/deepmerge.py
import yaml

from merg import DeepMerge

# Shared by Examples 1 and 2 only, so the two differ by merge options alone.
# Every scenario below owns its data locally.
SOURCE = {
    "server": {
        "port": 8080,
        "host": "localhost",
        "tags": ["dev"]
    }
}

TARGET = {
    "server": {
        "port": 80,
        "tags": ["base", "http"]
    },
    "database": "postgres"
}

def print_scenario(title, data):
    print(f"\n--- {title} ---")
    print(yaml.dump(data, sort_keys=False))

# Example 1: Default Merge (positional, by list index)
def example_default_merge():
    merg = DeepMerge()
    merged = merg.merge(TARGET, SOURCE)
    print_scenario("Example 1: Default Merge", merged)

# Example 2: Extend List
def example_extend_list():
    merg = DeepMerge(extend_existing_list=True)
    merged = merg.merge(TARGET, SOURCE)
    print_scenario("Example 2: Extend List (Interleave)", merged)

# --- Real World Scenarios ---

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

    merg = DeepMerge()
    merged = merg.merge(default_config, user_config)
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
    merg = DeepMerge(extend_existing_list=True, deduplicate_list=True)
    merged = merg.merge(base_role, admin_overlay)
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

    merg = DeepMerge(exclude_paths=["internal"])
    merged = merg.merge(current_user, update_payload)
    print_scenario("Scenario 5: Secure Merge (Excluding 'internal')", merged)

# Scenario 6: Knockout Prefix (Removing items via override)
def scenario_knockout_merge():
    # An ops team has a base feature-flag config and a regional override
    # that needs to disable a few features and add new ones.
    base_config = {
        "features": ["beta", "telemetry", "experimental_ui", "ads"],
        "regions": {"primary": "us-east", "fallback": "us-west"}
    }
    region_override = {
        # Remove 'telemetry' and 'ads', then add 'gdpr_banner'
        "features": ["--telemetry", "--ads", "gdpr_banner"],
        # Remove the fallback region key for this deployment (payload form)
        "regions": {"--fallback": ""}
    }

    merg = DeepMerge(knockout_prefix="--")
    merged = merg.merge(base_config, region_override)
    print_scenario("Scenario 6: Knockout Prefix (List removal + key removal)", merged)

if __name__ == "__main__":
    example_default_merge()
    example_extend_list()
    scenario_config_merge()
    scenario_permissions_merge()
    scenario_secure_merge()
    scenario_knockout_merge()
