import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("typecheck", ["npm", "run", "typecheck"]),
    ("smoke", ["npm", "run", "smoke"]),
    ("api-contract", ["npm", "run", "api-contract"]),
    ("feishu-card-fixture", ["npm", "run", "feishu-card-fixture"]),
    ("reporting-fixture", ["npm", "run", "reporting-fixture"]),
    ("reelfarm-projection-fixture", ["npm", "run", "reelfarm-projection-fixture"]),
    ("frontend-regression", ["npm", "run", "frontend-regression"]),
    ("account-pool-regression", ["npm", "run", "account-pool-regression"]),
    ("architecture-boundaries", ["npm", "run", "architecture-boundaries"]),
]


def main():
    for label, command in CHECKS:
        print(f"\n== {label} ==")
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            return result.returncode
    print("\nquality checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
