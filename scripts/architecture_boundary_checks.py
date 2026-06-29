import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE_ROOTS = ("api", "server_modules")
PUBLISH_CHECK_SEARCH_ROOTS = ("api", "app", "components", "hooks", "lib", "server_modules", "scripts")
PUBLISH_CHECK_REMOVED_FILES = (
    "api/routes/publish_check.py",
    "hooks/usePublishCheck.ts",
    "lib/api/publishCheck.ts",
    "server_modules/services/publish_check_runtime.py",
    "server_modules/services/publish_check_service.py",
)
PUBLISH_CHECK_TOKENS = (
    "Publish" + "Check",
    "publish" + "Check",
    "publish" + "-check",
    "publish" + "_check",
    "PUBLISH" + "_CHECK",
)
FIXED_GROWTH_CRON_PATHS = {
    "/api/growth/sync-db",
    "/api/growth/sync-dm",
    "/api/growth/sync-dl",
}


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


def publish_check_reference_offenders():
    offenders = []
    ignored = {Path(__file__).resolve()}
    for module_root in PUBLISH_CHECK_SEARCH_ROOTS:
        for path in (ROOT / module_root).rglob("*"):
            if path.resolve() in ignored or not path.is_file():
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".css"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(token in text for token in PUBLISH_CHECK_TOKENS):
                offenders.append(str(path.relative_to(ROOT)))
    return offenders


def assert_publish_check_removed():
    existing_removed_files = [path for path in PUBLISH_CHECK_REMOVED_FILES if (ROOT / path).exists()]
    offenders = publish_check_reference_offenders()
    problems = []
    if existing_removed_files:
        problems.append("removed files still exist: " + ", ".join(existing_removed_files))
    if offenders:
        problems.append("publish check references remain: " + ", ".join(offenders))
    if problems:
        raise AssertionError("; ".join(problems))


def assert_dynamic_growth_cron():
    config_path = ROOT / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cron_paths = {item.get("path") for item in config.get("crons") or []}
    fixed_paths = sorted(cron_paths & FIXED_GROWTH_CRON_PATHS)
    if fixed_paths:
        raise AssertionError("fixed product growth cron paths remain: " + ", ".join(fixed_paths))
    if "/api/growth/sync-all" not in cron_paths:
        raise AssertionError("dynamic growth cron path /api/growth/sync-all is missing")


def main():
    try:
        assert_no_runtime_server_imports()
        assert_publish_check_removed()
        assert_dynamic_growth_cron()
    except AssertionError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
    print("architecture boundary checks passed")


if __name__ == "__main__":
    main()
