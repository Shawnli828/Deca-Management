import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE_ROOTS = ("api", "server_modules")


def imports_server_module(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "server" for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and node.module == "server":
            return True
    return False


def runtime_server_import_offenders():
    offenders = []
    for module_root in RUNTIME_MODULE_ROOTS:
        for path in (ROOT / module_root).rglob("*.py"):
            if imports_server_module(path):
                offenders.append(str(path.relative_to(ROOT)))
    return offenders


def assert_no_runtime_server_imports():
    offenders = runtime_server_import_offenders()
    if offenders:
        raise AssertionError(
            "runtime modules should not import server.py directly: "
            + ", ".join(offenders)
        )


def main():
    try:
        assert_no_runtime_server_imports()
    except AssertionError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
    print("architecture boundary checks passed")


if __name__ == "__main__":
    main()
