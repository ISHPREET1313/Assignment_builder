"""
AutoDocSystem — main entry point
Run: python main.py
"""

import sys
import os

# ── Fix blurry GUI on Windows high-DPI screens ───────────────────────────────
if sys.platform == "win32":
    try:
        from ctypes import windll
        # Per-monitor DPI aware (best for multi-monitor setups)
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

sys.path.insert(0, os.path.dirname(__file__))

from app.gui import launch
from app.splash import SplashScreen


def main():
    def on_done(x=0, y=0):
        launch(x=x, y=y)

    SplashScreen(on_done=on_done).run()


if __name__ == "__main__":
    main()
