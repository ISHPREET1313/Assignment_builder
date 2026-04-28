"""
app/modules/code_mapper.py

Multi-strategy file finder. Tries progressively looser matches so it
handles every naming convention students actually use:

    exp1.py   Exp1.py   EXP_1.py   q1.c   Q1.c   prac1.cpp
    practical_1.c   assignment1.cpp   1.py   prog1.c
    experiment1.c   lab1.py   pr1.c

Strategy order (first match wins):
  1. Exact stem match              "1"    → "1.py"
  2. Stem equals prefix+no        "1"    → "exp1.py", "q1.c", "Q1.c"
  3. Stem ends with number        "1"    → anything ending in "1"
  4. Stem contains number anywhere "1"   → anything with "1" in it
     (but NOT if it also contains another digit adjacent, e.g. skip "12.py"
      when looking for "1")
"""

import re
from pathlib import Path

SUPPORTED = {".py", ".c", ".cpp", ".cc", ".cxx"}


def _files_in(folder: Path) -> list[Path]:
    try:
        return [p for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED]
    except PermissionError:
        return []


class CodeMapper:
    def __init__(self, code_dir: Path):
        self.code_dir = Path(code_dir).resolve()

    # ── Public ──────────────────────────────────────────────────────────────

    def find(self, exp_no: str) -> Path | None:
        """Return best-matching source file for *exp_no*, or None."""
        files = _files_in(self.code_dir)
        if not files:
            return None

        no = exp_no.strip()

        # Try each strategy in order
        for strategy in (
            self._exact,
            self._prefix_then_no,
            self._ends_with_no,
            self._contains_no_isolated,
        ):
            result = strategy(files, no)
            if result:
                return result

        return None

    def all_files(self) -> list[Path]:
        """Return all supported source files in the folder (for diagnostics)."""
        return sorted(_files_in(self.code_dir), key=lambda p: p.name.lower())

    # ── Strategies ──────────────────────────────────────────────────────────

    @staticmethod
    def _exact(files, no) -> Path | None:
        """Stem == exp_no exactly  (e.g. "1.py" for exp_no "1")"""
        for f in files:
            if f.stem.lower() == no.lower():
                return f
        return None

    @staticmethod
    def _prefix_then_no(files, no) -> Path | None:
        """
        Stem is letters/underscores followed immediately by exp_no
        and nothing after.   q1  Q1  exp1  EXP_1  prac1  lab1 …
        """
        pattern = re.compile(
            rf"^[a-z_\-]*{re.escape(no)}$", re.IGNORECASE
        )
        hits = [f for f in files if pattern.match(f.stem)]
        if hits:
            hits.sort(key=lambda f: len(f.stem))   # prefer shorter names
            return hits[0]
        return None

    @staticmethod
    def _ends_with_no(files, no) -> Path | None:
        """
        Stem ends with exp_no, not immediately preceded by another digit.
        Catches  practical_1  assignment1  program_01 …
        """
        pattern = re.compile(
            rf"(?<!\d){re.escape(no)}$", re.IGNORECASE
        )
        hits = [f for f in files if pattern.search(f.stem)]
        if hits:
            hits.sort(key=lambda f: len(f.stem))
            return hits[0]
        return None

    @staticmethod
    def _contains_no_isolated(files, no) -> Path | None:
        """
        exp_no appears anywhere in stem, surrounded by non-digits.
        Last resort — avoids matching "12" when looking for "1".
        """
        pattern = re.compile(
            rf"(?<!\d){re.escape(no)}(?!\d)", re.IGNORECASE
        )
        hits = [f for f in files if pattern.search(f.stem)]
        if hits:
            hits.sort(key=lambda f: len(f.stem))
            return hits[0]
        return None
