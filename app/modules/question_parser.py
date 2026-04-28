"""
app/modules/question_parser.py

questions.txt format (blocks separated by blank lines):
─────────────────────────────────────────────────────────
EXP: 1
QUESTION: Write a Python program to add two numbers.
INPUT: 3 5

EXP: 2
QUESTION: Check if a number is prime.
INPUT: 17
─────────────────────────────────────────────────────────

inputs.txt format (optional, overrides inline INPUT):
─────────────────────────────────────────────────────────
EXP: 1
INPUT: 3 5

EXP: 2
INPUT: 17
─────────────────────────────────────────────────────────
Lines starting with '#' are ignored.
"""

import re
from pathlib import Path


class QuestionParser:
    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)

    def parse(self) -> list[dict]:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Questions file not found: {self.filepath}")

        text   = self.filepath.read_text(encoding="utf-8")
        blocks = re.split(r"\n{2,}", text.strip())
        entries = []

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            entry = {}
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, val = line.partition(":")
                key = key.strip().upper()
                val = val.strip()
                if key == "EXP":
                    entry["exp_no"] = val
                elif key == "QUESTION":
                    entry["question"] = val
                elif key == "INPUT":
                    entry["input"] = val

            if "exp_no" in entry and "question" in entry:
                entry.setdefault("input", "")
                entries.append(entry)

        return entries

    def merge_inputs(self, entries: list[dict], inputs_file: Path):
        """
        Read inputs.txt and override the 'input' field for matching exp_nos.
        Entries in inputs.txt that have no match in *entries* are ignored.
        """
        text   = inputs_file.read_text(encoding="utf-8")
        blocks = re.split(r"\n{2,}", text.strip())
        overrides: dict[str, str] = {}

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            exp_no = inp = None
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, val = line.partition(":")
                key = key.strip().upper()
                val = val.strip()
                if key == "EXP":
                    exp_no = val
                elif key == "INPUT":
                    inp = val
            if exp_no is not None and inp is not None:
                overrides[exp_no] = inp

        for entry in entries:
            if entry["exp_no"] in overrides:
                entry["input"] = overrides[entry["exp_no"]]
