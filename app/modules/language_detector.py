"""app/modules/language_detector.py"""
from pathlib import Path

EXT_MAP = {".py": "Python", ".c": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++"}


class LanguageDetector:
    def detect(self, filepath: Path) -> str:
        return EXT_MAP.get(Path(filepath).suffix.lower(), "Unknown")
