import ast
from pathlib import Path

import pytest

REPOSITORIES_DIR = Path(__file__).resolve().parents[2] / "repositories"


def duplicate_method_names(source):
    """Return class.method names that are defined more than once in one class body."""
    duplicates = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue

        seen = set()
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name in seen:
                duplicates.append(f"{node.name}.{item.name}")
            seen.add(item.name)
    return duplicates


@pytest.mark.parametrize(
    "repository_file",
    sorted(REPOSITORIES_DIR.glob("*_repository.py")),
    ids=lambda path: path.name,
)
def test_repository_classes_define_each_method_once(repository_file):
    source = repository_file.read_text(encoding="utf-8")

    assert duplicate_method_names(source) == []
