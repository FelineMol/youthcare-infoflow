"""
check_release.py — pre-publish safety gate.

Verifies that nothing private would be published:
  1. .gitignore covers the private paths;
  2. no private path is git-tracked (if this is a git repo);
  3. no e-mail-like string appears in any would-be-published text file;
  4. no e-mail-like string appears in any would-be-published .xlsx (e.g. mapping workbooks).

Exit code 0 = PASS, 1 = FAIL. Run before every publish / release.
"""
from __future__ import annotations
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Legitimate public contact e-mails may be whitelisted here once added (e.g. corresponding author).
ALLOWED_EMAILS: set[str] = set()

# Must never be published (mirror .gitignore).
PRIVATE_DIRS = ["data/raw", "data/qualitative", "outputs", ".venv", "venv", ".git",
                "__pycache__", ".ipynb_checkpoints"]
# The one intentional exception under outputs/: the rendered main figures are committed
# so readers/reviewers can see them without running the pipeline (mirror .gitignore).
PUBLISHED_OUTPUT_GLOBS = ["outputs/figures/Figure_*.png"]
PRIVATE_FILE_GLOBS = ["*.code-workspace", "HANDOFF-LOG.md", "~$*", "*.pyc", ".DS_Store",
                      # S6 holds participant quotes and is deliberately not published
                      "S6_qualitative_patterns*.csv"]
GITIGNORE_MUST_COVER = ["data/raw/", "data/qualitative/", "outputs/", ".venv/",
                        "*.code-workspace", "HANDOFF-LOG.md"]
TEXT_EXT = {".py", ".csv", ".md", ".cff", ".txt", ".yml", ".yaml", ".ini", ".toml"}


def is_private(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    if any(fnmatch(rel, g) for g in PUBLISHED_OUTPUT_GLOBS):
        return False
    if any(rel == d or rel.startswith(d + "/") for d in PRIVATE_DIRS):
        return True
    return any(p.match(g) for g in PRIVATE_FILE_GLOBS)


def _emails(text: str) -> set[str]:
    return {e for e in EMAIL.findall(text) if e not in ALLOWED_EMAILS}


def main() -> int:
    problems: list[str] = []

    # 1) .gitignore coverage
    gi = (ROOT / ".gitignore").read_text() if (ROOT / ".gitignore").exists() else ""
    for entry in GITIGNORE_MUST_COVER:
        if entry not in gi:
            problems.append(f".gitignore is missing an entry for: {entry}")

    # collect the would-be-published files
    publishable = [p for p in ROOT.rglob("*") if p.is_file() and not is_private(p)]

    # 3) e-mails in publishable text files
    for p in publishable:
        if p.suffix.lower() in TEXT_EXT or p.name == ".gitignore":
            hits = _emails(p.read_text(errors="ignore"))
            if hits:
                problems.append(f"e-mail(s) in publishable file {p.relative_to(ROOT)}: {sorted(hits)}")

    # 4) e-mails in publishable .xlsx (mapping workbooks etc.)
    try:
        import openpyxl
        for p in publishable:
            if p.suffix.lower() == ".xlsx":
                wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
                for ws in wb.worksheets:
                    for row in ws.iter_rows(values_only=True):
                        for v in row:
                            if isinstance(v, str) and _emails(v):
                                problems.append(f"e-mail in publishable xlsx {p.relative_to(ROOT)} (sheet {ws.title})")
                                break
                        else:
                            continue
                        break
    except ImportError:
        problems.append("(openpyxl not available — .xlsx e-mail scan skipped)")

    # 2) git-tracked private files
    if (ROOT / ".git").exists():
        tracked = subprocess.run(["git", "ls-files"], cwd=str(ROOT),
                                 capture_output=True, text=True).stdout.splitlines()
        for f in tracked:
            if is_private(ROOT / f):
                problems.append(f"PRIVATE file is git-tracked: {f}")
    else:
        print("note: not a git repository yet; initialise git before publishing, then re-run.")

    print(f"publishable files scanned: {len(publishable)}")
    if problems:
        print("\nFAIL — resolve before publishing:")
        for x in problems:
            print("  -", x)
        return 1
    print("\nPASS — no private paths in the publishable set; no e-mail-like strings found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
