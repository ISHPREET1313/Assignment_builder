"""
build.py — Creates a standalone .exe (Windows) or binary (Linux/macOS)
using PyInstaller.

Usage:
    pip install pyinstaller
    python build.py
"""

import subprocess
import sys
import shutil
from pathlib import Path

APP_NAME  = "AutoDocSystem"
MAIN      = "main.py"
ICON      = "assets/icon.ico"   # optional — remove --icon line if missing

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",                     # single .exe
    "--windowed",                    # no console window on Windows
    "--name", APP_NAME,
    "--add-data", f"sample{';' if sys.platform=='win32' else ':'}sample",
    "--hidden-import", "PIL._tkinter_finder",
    "--hidden-import", "customtkinter",
]

# Add icon if it exists
if Path(ICON).exists():
    cmd += ["--icon", ICON]

cmd.append(MAIN)

print("Building with PyInstaller…")
print(" ".join(cmd))
result = subprocess.run(cmd)

if result.returncode == 0:
    dist = Path("dist") / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
    print(f"\n✅  Built: {dist.resolve()}")
    print("Copy the dist/ folder to share with others.")
else:
    print("\n❌  Build failed — check output above.")
