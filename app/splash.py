import math
import random as _rnd
import tkinter as tk
from tkinter import font as tkfont

# ── Professional palette ────────────────────────────────────────────────────
BG       = "#0F172A"  # Deep navy
ACCENT   = "#38BDF8"  # Bright cyan
ACCENT2  = "#60A5FA"  # Soft sky blue
ACCENT3  = "#7DD3FC"  # Light aqua
GOLD     = "#94A3B8"  # Steel-gray accent
TEXT     = "#E2E8F0"  # Soft off-white
TEXT_DIM = "#94A3B8"  # Muted slate
MUTED    = "#64748B"  # Cool gray

# ── Timing (seconds) ──────────────────────────────────────────────────────────
T_CURSIVE_IN   = 0.35
T_CURSIVE_HOLD = 3.00
T_CURSIVE_OUT  = 3.40
T_EXPAND       = 3.80
T_BOLD_IN      = 3.90
T_SUBTITLE_IN  = 4.20
T_LINE_IN      = 4.35
T_DONE         = 4.95

TICK_MS   = 16          # ~60 fps
SPLASH_W  = 820         # starting window width
SPLASH_H  = 320         # starting window height
FULL_W    = 1020        # final window size (matches App geometry)
FULL_H    = 700


def _ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _ease_progress(elapsed: float, start: float, duration: float) -> float:
    return _ease_in_out(_clamp((elapsed - start) / duration, 0.0, 1.0))


class _Particle:
    __slots__ = ("x", "y", "r", "vx", "vy", "phase", "color")

    def __init__(self, w: int, h: int):
        self.x     = _rnd.uniform(0, w)
        self.y     = _rnd.uniform(0, h)
        self.r     = _rnd.uniform(1.0, 2.8)
        self.vx    = _rnd.uniform(-0.15, 0.15)
        self.vy    = _rnd.uniform(-0.35, -0.08)
        self.phase = _rnd.uniform(0, math.tau)
        self.color = ACCENT if _rnd.random() < 0.55 else GOLD

    def step(self, h: int):
        self.x     += self.vx
        self.y     += self.vy
        self.phase += 0.022
        if self.y < -4:
            self.y = h + 4


class SplashScreen:
    """
    Call SplashScreen(on_done=callback).run() — blocks until animation finishes,
    then calls on_done() so the caller can launch the main App window.
    """

    N_PARTICLES = 32

    def __init__(self, on_done=None):
        self._on_done = on_done
        self._elapsed = 0.0
        self._done    = False

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 1.0)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - SPLASH_W) // 2
        y  = (sh - SPLASH_H) // 2
        self.root.geometry(f"{SPLASH_W}x{SPLASH_H}+{x}+{y}")

        self._sw = sw
        self._sh = sh

        self.cv = tk.Canvas(
            self.root,
            width=SPLASH_W, height=SPLASH_H,
            bg=BG, highlightthickness=0,
        )
        self.cv.pack(fill="both", expand=True)

        try:
            self._f_cursive  = tkfont.Font(family="Georgia", size=46, slant="italic")
            self._f_subtitle_cursive = tkfont.Font(family="Georgia", size=13, slant="italic")
            self._f_bold     = tkfont.Font(family="Georgia", size=34, weight="bold")
            self._f_subtitle = tkfont.Font(family="Georgia", size=12)
            self._f_small    = tkfont.Font(family="Georgia", size=9)
        except Exception:
            self._f_cursive          = tkfont.Font(size=46, slant="italic")
            self._f_subtitle_cursive = tkfont.Font(size=13, slant="italic")
            self._f_bold             = tkfont.Font(size=34, weight="bold")
            self._f_subtitle         = tkfont.Font(size=12)
            self._f_small            = tkfont.Font(size=9)

        _rnd.seed()
        self._particles = [_Particle(SPLASH_W, SPLASH_H) for _ in range(self.N_PARTICLES)]

        self._items: dict = {}
        self._build_canvas_items()

    def _build_canvas_items(self):
        cv = self.cv
        cx = SPLASH_W // 2
        cy = SPLASH_H // 2

        self._p_ids = []
        for p in self._particles:
            oid = cv.create_oval(p.x-p.r, p.y-p.r, p.x+p.r, p.y+p.r,
                                 fill=p.color, outline="", state="hidden")
            self._p_ids.append(oid)

        self._items["cursive"] = cv.create_text(
            cx, cy, text="Assignment Builder",
            font=self._f_cursive, fill=TEXT, state="hidden")

        self._items["cursive_sub"] = cv.create_text(
            cx, cy + 42, text="document automation system",
            font=self._f_subtitle_cursive, fill=TEXT_DIM, state="hidden")

        self._items["bold"] = cv.create_text(
            cx, cy - 10, text="✿ AutoDocSystem",
            font=self._f_bold, fill=ACCENT, state="hidden")

        self._items["bold_sub"] = cv.create_text(
            cx, cy + 30, text="Practical Documentation Generator",
            font=self._f_subtitle, fill=TEXT_DIM, state="hidden")

        self._items["line"] = cv.create_rectangle(
            cx, cy + 48, cx, cy + 49,
            fill=MUTED, outline="", state="hidden")

        self._items["version"] = cv.create_text(
            cx, SPLASH_H - 18, text="v1.0.0",
            font=self._f_small, fill=MUTED, state="hidden")

    def _render(self):
        cv   = self.cv
        e    = self._elapsed
        W    = self._cur_w
        H    = self._cur_h
        cx   = W // 2
        cy   = H // 2

        for i, p in enumerate(self._particles):
            p.step(H)
            alpha = int(_clamp(0.18 + 0.22 * math.sin(p.phase), 0.05, 0.45) * 255)
            col   = _hex_alpha(p.color, alpha)
            oid   = self._p_ids[i]
            cv.coords(oid, p.x-p.r, p.y-p.r, p.x+p.r, p.y+p.r)
            cv.itemconfigure(oid, fill=col, state="normal")

        if T_CURSIVE_IN <= e < T_CURSIVE_OUT + 0.8:
            if e < T_CURSIVE_HOLD:
                p_ = _ease_progress(e, T_CURSIVE_IN, 0.9)
                op = p_
                y_off = _lerp(22, 0, p_)
            elif e < T_CURSIVE_OUT:
                op    = 1.0
                y_off = math.sin(e * 1.8) * 2.5
            else:
                p_ = _ease_progress(e, T_CURSIVE_OUT, 0.75)
                op    = 1.0 - p_
                y_off = _lerp(0, -26, p_)

            col_main = _hex_alpha(TEXT,     int(op * 255))
            col_sub  = _hex_alpha(TEXT_DIM, int(op * 0.65 * 255))
            cv.coords(self._items["cursive"],     cx, cy - 6  + y_off)
            cv.coords(self._items["cursive_sub"], cx, cy + 36 + y_off)
            cv.itemconfigure(self._items["cursive"],     fill=col_main, state="normal")
            cv.itemconfigure(self._items["cursive_sub"], fill=col_sub,  state="normal")
        else:
            cv.itemconfigure(self._items["cursive"],     state="hidden")
            cv.itemconfigure(self._items["cursive_sub"], state="hidden")

        if e >= T_BOLD_IN:
            p_ = _ease_progress(e, T_BOLD_IN, 0.65)
            op    = p_
            y_off = _lerp(24, 0, p_)
            col   = _hex_alpha(ACCENT, int(op * 255))
            cv.coords(self._items["bold"], cx, cy - 14 + y_off)
            cv.itemconfigure(self._items["bold"], fill=col, state="normal")
        else:
            cv.itemconfigure(self._items["bold"], state="hidden")

        if e >= T_SUBTITLE_IN:
            p_ = _ease_progress(e, T_SUBTITLE_IN, 0.5)
            col = _hex_alpha(TEXT_DIM, int(p_ * 200))
            cv.coords(self._items["bold_sub"], cx, cy + 24)
            cv.itemconfigure(self._items["bold_sub"], fill=col, state="normal")
        else:
            cv.itemconfigure(self._items["bold_sub"], state="hidden")

        if e >= T_LINE_IN:
            p_   = _ease_progress(e, T_LINE_IN, 0.6)
            half = int(p_ * 140)
            cv.coords(self._items["line"],
                      cx - half, cy + 41,
                      cx + half, cy + 42)
            cv.itemconfigure(self._items["line"],
                             fill=_hex_alpha(MUTED, int(p_ * 180)),
                             state="normal")
        else:
            cv.itemconfigure(self._items["line"], state="hidden")

        if e >= T_SUBTITLE_IN:
            p_ = _ease_progress(e, T_SUBTITLE_IN, 0.4)
            cv.coords(self._items["version"], cx, H - 18)
            cv.itemconfigure(self._items["version"],
                             fill=_hex_alpha(MUTED, int(p_ * 160)),
                             state="normal")
        else:
            cv.itemconfigure(self._items["version"], state="hidden")

    def _update_geometry(self):
        e = self._elapsed
        if e < T_EXPAND:
            self._cur_w = SPLASH_W
            self._cur_h = SPLASH_H
            return

        p_ = _ease_progress(e, T_EXPAND, 0.55)
        w  = int(_lerp(SPLASH_W, FULL_W, p_))
        h  = int(_lerp(SPLASH_H, FULL_H, p_))
        if w != self._cur_w or h != self._cur_h:
            self._cur_w = w
            self._cur_h = h
            x = (self._sw - w) // 2
            y = (self._sh - h) // 2
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.cv.configure(width=w, height=h)

    def _tick(self):
        if self._done:
            return

        self._elapsed  += TICK_MS / 1000.0
        self._update_geometry()
        self._render()

        if self._elapsed >= T_DONE:
            self._finish()
            return

        self.root.after(TICK_MS, self._tick)

    def _finish(self):
        self._done = True
        self.root.destroy()
        if self._on_done:
            self._on_done()

    def run(self):
        self._cur_w = SPLASH_W
        self._cur_h = SPLASH_H
        self.root.after(TICK_MS, self._tick)
        self.root.mainloop()


def _hex_alpha(hex_color: str, alpha: int) -> str:
    t  = alpha / 255.0
    sr, sg, sb = _hex_to_rgb(hex_color)
    br, bg_, bb = _hex_to_rgb(BG)
    r  = int(_lerp(br, sr, t))
    g  = int(_lerp(bg_, sg, t))
    b  = int(_lerp(bb, sb, t))
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
