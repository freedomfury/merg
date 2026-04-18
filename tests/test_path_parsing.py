from merg.core import DeepMerge

def test_ast_path_parsing_dot_notation():
    merger = DeepMerge(exclude_paths=["server.config.port"])
    assert ("server", "config", "port") in merger.options["exclude_paths"]

def test_ast_path_parsing_bracket_notation():
    merger = DeepMerge(exclude_paths=["server['config']['port']"])
    assert ("server", "config", "port") in merger.options["exclude_paths"]

def test_ast_path_parsing_list_index():
    merger = DeepMerge(exclude_paths=["servers[0]['port']"])
    assert ("servers", 0, "port") in merger.options["exclude_paths"]

def test_ast_path_parsing_mixed():
    merger = DeepMerge(exclude_paths=["servers[0].config['port']"])
    assert ("servers", 0, "config", "port") in merger.options["exclude_paths"]

def test_ast_path_parsing_invalid_syntax_fallback():
    # If AST fails, it should fallback to split('.') or at least be robust
    # The current implementation falls back to split('.')
    merger = DeepMerge(exclude_paths=["simple.path"])
    assert ("simple", "path") in merger.options["exclude_paths"]


# -----------------------------------------------------------------------------
# Real-world key names that don't parse as Python identifiers
# (Kubernetes, Helm, Docker labels, etc. commonly use dashes/dots/slashes.)
# -----------------------------------------------------------------------------

def test_path_parsing_dashed_key():
    """Keys with dashes (e.g. 'my-app') must not crash."""
    merger = DeepMerge(exclude_paths=["my-app"])
    # Dashes parse as a BinOp(Sub) in AST; should fall back to literal-key tuple
    assert ("my-app",) in merger.options["exclude_paths"]


def test_path_parsing_dashed_nested_key():
    """Dashed key inside a dotted path falls back to literal split."""
    merger = DeepMerge(exclude_paths=["spec.my-app.value"])
    assert ("spec", "my-app", "value") in merger.options["exclude_paths"]


def test_path_parsing_python_keyword_as_key():
    """Python keywords as keys (e.g. 'True', 'class') must not crash."""
    merger = DeepMerge(exclude_paths=["True.x"])
    assert ("True", "x") in merger.options["exclude_paths"]


def test_path_parsing_slash_in_key():
    """K8s-style keys with slashes (e.g. 'app.kubernetes.io/name') don't crash."""
    merger = DeepMerge(exclude_paths=["app.kubernetes.io/name"])
    # Slash is invalid in Python identifiers — must fall back gracefully
    assert merger.options["exclude_paths"]  # at minimum, no crash


def test_path_parsing_numeric_segment_in_dotted_path():
    """A path segment that's purely numeric (e.g. '123.x') doesn't crash."""
    # AST parses '123.x' as Attribute(value=Constant(123), attr='x')
    # which currently happens to work but produced ('123', 'x') by string fallback
    merger = DeepMerge(exclude_paths=["123.x"])
    assert merger.options["exclude_paths"]  # at minimum, no crash


def test_bracket_notation_still_works_for_clean_paths():
    """Regression: ensure the AST path still works for paths it should handle."""
    merger = DeepMerge(exclude_paths=["users[0]['name']"])
    assert ("users", 0, "name") in merger.options["exclude_paths"]
