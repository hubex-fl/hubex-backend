import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = "docs/CHANGELOG.md"
ALLOWLIST_PREFIXES = ("docs/",)


def _git_changed_files() -> list[str]:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        base_ref = None
        if "GITHUB_BASE_REF" in os.environ:
            base_ref = f"origin/{os.environ['GITHUB_BASE_REF']}"
        for candidate in (base_ref, "origin/main", "origin/master"):
            if not candidate:
                continue
            try:
                subprocess.run(
                    ["git", "rev-parse", "--verify", candidate],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                diff_cmd = ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{candidate}...HEAD"]
                result = subprocess.run(
                    diff_cmd,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                files = [line for line in result.stdout.splitlines() if line.strip()]
                return files
            except subprocess.CalledProcessError:
                continue

    staged = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRT", "--cached"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    unstaged = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRT"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    files = [f for f in staged + unstaged + untracked if f.strip()]
    return sorted(set(files))


def _is_allowlisted(path: str) -> bool:
    if path == CHANGELOG:
        return True
    return path.startswith(ALLOWLIST_PREFIXES)


def main() -> int:
    files = _git_changed_files()
    if not files:
        print("changelog gate ok (no changes)")
        return 0
    has_changelog = CHANGELOG in files
    requires_entry = any(not _is_allowlisted(f) for f in files)
    if requires_entry and not has_changelog:
        print("changelog entry required: update docs/CHANGELOG.md", file=sys.stderr)
        print("changed files:", file=sys.stderr)
        for f in files:
            print(f, file=sys.stderr)
        return 1
    print("changelog gate ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
