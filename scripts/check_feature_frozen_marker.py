import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SSOT = REPO_ROOT / "hubex_state.md"
MARKER = "Phase-1 COMPLETE / FEATURE-FROZEN"


def main() -> int:
    if not SSOT.exists():
        print("feature freeze check failed: hubex_state.md missing")
        return 1
    text = SSOT.read_text(encoding="utf-8", errors="replace")
    if MARKER not in text:
        print(f"feature freeze check failed: marker not found: {MARKER}")
        return 1
    print("feature freeze marker ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
