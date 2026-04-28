"""
app/modules/output_handler.py  v4

High-resolution crisp terminal output image.
- Renders at 3× scale then saves at 144 DPI — looks sharp on any screen/printer
- Uses DejaVu Mono or falls back gracefully
- Proper word-wrap for long lines
- Dark terminal style matching VS Code integrated terminal
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Terminal colours (VS Code dark terminal)
BG      = (12,  12,  12)     # near-black
FG      = (204, 204, 204)    # light grey text
ERR_FG  = (255, 100,  90)    # red for errors
OK_FG   = (78,  201, 176)    # teal for success markers
PROMPT  = (87,  166, 74)     # green dollar sign

# Render at this scale, then down-sample for crisp result
SCALE   = 3
BASE_FS = 14          # base font size (will be multiplied by SCALE)
PAD     = 20 * SCALE
LINE_SP = 6 * SCALE   # extra spacing between lines
MAX_W   = 900 * SCALE # max image width in scaled pixels


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "DejaVuSansMono.ttf",
        "LiberationMono-Regular.ttf",
        "UbuntuMono-R.ttf",
        "Courier New.ttf",
        "cour.ttf",
        "consola.ttf",
        "lucon.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
    # Final fallback — PIL built-in (no size control but always works)
    return ImageFont.load_default()


def _wrap_line(text: str, font, max_px: int, draw) -> list[str]:
    """Wrap a single line to fit within max_px."""
    if draw.textlength(text, font=font) <= max_px:
        return [text]
    words   = list(text)   # char-level wrap for code
    lines   = []
    current = ""
    for ch in text:
        test = current + ch
        if draw.textlength(test, font=font) > max_px:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines if lines else [text]


class OutputHandler:
    def __init__(self, img_dir: Path):
        self.img_dir = Path(img_dir)
        self.img_dir.mkdir(parents=True, exist_ok=True)

    def to_image(self, text: str, exp_no: str) -> Path:
        fs   = BASE_FS * SCALE
        font = _load_font(fs)
        lh   = fs + LINE_SP     # line height

        raw_lines = text.splitlines() if text.strip() else ["(no output)"]

        # First pass: measure & wrap
        dummy_img  = Image.new("RGB", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        usable_w   = MAX_W - PAD * 2
        wrapped: list[tuple[str, str]] = []   # (text, colour_key)

        is_err = False
        for line in raw_lines:
            if line.startswith("[ERROR") or line.startswith("[Compilation"):
                is_err = True
            colour = "err" if is_err else "fg"
            sub = _wrap_line(line, font, usable_w, dummy_draw)
            for sl in sub:
                wrapped.append((sl, colour))

        # Measure actual widths
        widths = [dummy_draw.textlength(t, font=font) for t, _ in wrapped]
        img_w  = min(int(max(widths, default=200)) + PAD * 2, MAX_W)
        img_h  = lh * len(wrapped) + PAD * 2 + lh   # +1 line for header

        img  = Image.new("RGB", (img_w, img_h), BG)
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle([(0, 0), (img_w, lh + PAD // 2)],
                        fill=(30, 30, 30))
        draw.text((PAD, PAD // 3),
                  f"  ●  Experiment {exp_no} — Output",
                  font=font, fill=(140, 140, 140))

        y = lh + PAD
        colour_map = {
            "fg" : FG,
            "err": ERR_FG,
        }
        for line_text, colour_key in wrapped:
            draw.text((PAD, y), line_text,
                      font=font, fill=colour_map[colour_key])
            y += lh

        # Down-sample to 1× for sharp result
        final_w = img_w  // SCALE
        final_h = img_h  // SCALE
        img = img.resize((final_w, final_h), Image.LANCZOS)

        out = self.img_dir / f"exp{exp_no}_out.png"
        img.save(str(out), "PNG", dpi=(144, 144))
        return out
