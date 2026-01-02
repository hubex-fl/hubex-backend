import re
import subprocess
import sys


def main() -> int:
    proc = subprocess.run(["alembic", "heads"], capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode

    heads = [line for line in proc.stdout.splitlines() if re.search(r"\(head\)", line)]
    if len(heads) != 1:
        print("alembic heads check failed:")
        print(proc.stdout)
        return 1

    print("alembic heads ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
