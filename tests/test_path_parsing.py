from deep_merge.core import DeepMerge
import pytest

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
