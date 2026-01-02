import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

LF_EXTS = {".py", ".sh", ".yml", ".yaml", ".md", ".json"}
CRLF_EXTS = {".ps1"}


def git_changed_files() -> list[str]:
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
                if files:
                    return files
                break
            except subprocess.CalledProcessError:
                continue

    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRT", "--cached"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [line for line in result.stdout.splitlines() if line.strip()]
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRT"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files.extend([line for line in result.stdout.splitlines() if line.strip()])
    return sorted(set(files))


def check_eol(path: Path, rel: str, errors: list[str]) -> None:
    suffix = path.suffix.lower()
    if suffix not in LF_EXTS and suffix not in CRLF_EXTS:
        return
    try:
        data = path.read_bytes()
    except OSError:
        return
    if suffix in LF_EXTS and b"\r\n" in data:
        errors.append(f"EOL CRLF not allowed in {rel}")
    if suffix in CRLF_EXTS and b"\r\n" not in data and b"\n" in data:
        errors.append(f"EOL CRLF required in {rel}")


def check_trailing_whitespace(path: Path, rel: str, errors: list[str]) -> None:
    if not (rel.startswith("docs/") or rel.startswith("scripts/")):
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for idx, line in enumerate(text.splitlines(), start=1):
        if line.rstrip() != line:
            errors.append(f"TRAILING WS {rel}:{idx}")


def main() -> int:
    errors: list[str] = []
    changed = git_changed_files()
    if not changed:
        print("repo hygiene ok (no changed files)")
        return 0
    for rel in changed:
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        check_eol(path, rel, errors)
        check_trailing_whitespace(path, rel, errors)
    if errors:
        print("repo hygiene check failed:")
        for err in errors:
            print(err)
        return 1
    print("repo hygiene ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
