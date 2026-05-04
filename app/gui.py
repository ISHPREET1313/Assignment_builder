"""
app/gui.py  —  AutoDocSystem  v4

Tabs:
  ⚙  Setup       — template, code folder, output folder + live folder scanner
  ▤  Experiments  — built-in editor with auto-detect, import/export
  ▶  Log          — dark terminal + progress

Session is auto-saved to session.json next to main.py on every change and
on close, and auto-loaded on startup.
"""

import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from app.pipeline import Pipeline

# ── Palette ──────────────────────────────────────────────────────────────────
C = {
    # Core backgrounds
    "bg"          : "#0D0F12",   # Near-black base
    "sidebar"     : "#080A0C",   # Sidebar void
    "card"        : "#13161A",   # Elevated surface
    "card_hover"  : "#1A1E24",   # Hover surface

    # Accent — single electric cyan
    "accent"      : "#00D4FF",   # Primary cyan
    "accent2"     : "#33DEFF",   # Lighter cyan hover
    "accent_dim"  : "#00708A",   # Muted cyan
    "accent_glow" : "#003A47",   # Glow bg behind accent

    # Status
    "success"     : "#00E5A0",   # Emerald green
    "warn"        : "#F5A623",   # Amber
    "err"         : "#FF4757",   # Red

    # Text
    "text"        : "#E8EDF2",   # Primary text
    "text_dim"    : "#8A95A3",   # Secondary / muted
    "muted"       : "#3D4550",   # Very muted

    # Inputs / borders
    "entry"       : "#0A0C0F",
    "border"      : "#1E2530",
    "border_focus": "#00D4FF",

    # Log
    "log_bg"      : "#060809",
    "log_text"    : "#6EE7FF",

    # Table
    "row_alt"     : "#0F1216",
    "row_sel"     : "#0A2A33",
}

F_BODY  = ("Consolas", 10)
F_BOLD  = ("Consolas", 10, "bold")
F_TITLE = ("Consolas", 13, "bold")
F_SMALL = ("Consolas", 9)
F_MONO  = ("Consolas", 9)
F_MONO_B= ("Consolas", 9, "bold")
F_HEAD  = ("Consolas", 11, "bold")

NAV = [
    ("⚙",  "Setup",       "Configure paths & template"),
    ("▤",  "Experiments", "Manage practicals"),
    ("▶",  "Log",         "Run & view output"),
]

SESSION_FILE = Path(__file__).parent.parent / "session.json"


# ── Small widget helpers ─────────────────────────────────────────────────────

def btn(parent, text, cmd, bg=None, fg=None, font=None, px=14, py=7, hover=None):
    b = tk.Button(
        parent, text=text, command=cmd,
        font=font or F_BOLD,
        bg=bg or C["accent"], fg=fg or C["bg"],
        activebackground=hover or C["accent2"],
        activeforeground=C["bg"],
        relief="flat", padx=px, pady=py, cursor="hand2", bd=0)
    b._original_bg = bg or C["accent"]
    b._hover_bg    = hover or (C["accent2"] if (bg or C["accent"]) == C["accent"] else C["card_hover"])
    b.bind("<Enter>", lambda e: b.configure(bg=b._hover_bg))
    b.bind("<Leave>", lambda e: b.configure(bg=b._original_bg))
    return b

def lbl(parent, text, font=None, fg=None, bg=None, **kw):
    return tk.Label(
        parent, text=text, font=font or F_BODY,
        fg=fg or C["text"], bg=bg or C["bg"], **kw)

def entry(parent, var, width=40):
    ent = tk.Entry(
        parent, textvariable=var, font=F_BODY,
        bg=C["entry"], fg=C["text"], insertbackground=C["accent"],
        relief="flat",
        highlightbackground=C["border"],
        highlightthickness=1, width=width)
    ent.bind("<FocusIn>",  lambda e: ent.configure(
        highlightbackground=C["border_focus"], highlightthickness=1))
    ent.bind("<FocusOut>", lambda e: ent.configure(
        highlightbackground=C["border"], highlightthickness=1))
    return ent

def frm(parent, bg=None, **kw):
    return tk.Frame(parent, bg=bg or C["bg"], **kw)

def sep(parent, orient="horizontal"):
    if orient == "horizontal":
        return tk.Frame(parent, bg=C["border"], height=1)
    return tk.Frame(parent, bg=C["border"], width=1)

def textbox(parent, font=None, height=5, **kw):
    return tk.Text(
        parent, font=font or F_MONO,
        bg=C["entry"], fg=C["text"],
        insertbackground=C["accent"],
        relief="flat",
        highlightbackground=C["border"],
        highlightthickness=1,
        height=height, **kw)

def tag_lbl(parent, text, color=None):
    """Small inline badge/tag label."""
    color = color or C["accent"]
    f = tk.Frame(parent, bg=C["accent_glow"], padx=6, pady=1)
    tk.Label(f, text=text, font=("Consolas", 8, "bold"),
             bg=C["accent_glow"], fg=color).pack()
    return f


# ── Session persistence ──────────────────────────────────────────────────────

def load_session() -> dict:
    try:
        if SESSION_FILE.exists():
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_session(data: dict):
    try:
        SESSION_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        pass


# ── Main App ─────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoDocSystem — Practical Documentation Generator")
        self.geometry("1060x700")
        self.minsize(860, 580)
        self.configure(bg=C["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._queue: queue.Queue = queue.Queue()
        self._running  = False
        self._experiments: list[dict] = []

        self._build()
        self._load_session()
        self._poll()
        self._switch_tab("Setup")

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ───────────────────────────────────────────────────────────
        hdr = frm(self, bg=C["sidebar"])
        hdr.pack(fill="x")

        # Thin top accent line
        tk.Frame(hdr, bg=C["accent"], height=2).pack(fill="x", side="top")

        inner_hdr = frm(hdr, bg=C["sidebar"])
        inner_hdr.pack(fill="x", padx=20, pady=10)

        # Left: logo + title
        logo_area = frm(inner_hdr, bg=C["sidebar"])
        logo_area.pack(side="left")

        # Monogram badge
        badge = tk.Frame(logo_area, bg=C["accent"], width=32, height=32)
        badge.pack(side="left", padx=(0, 12))
        badge.pack_propagate(False)
        tk.Label(badge, text="AD", font=("Consolas", 9, "bold"),
                 bg=C["accent"], fg=C["bg"]).place(relx=.5, rely=.5, anchor="center")

        text_area = frm(logo_area, bg=C["sidebar"])
        text_area.pack(side="left")
        tk.Label(text_area, text="AutoDocSystem",
                 font=("Consolas", 14, "bold"),
                 bg=C["sidebar"], fg=C["text"]).pack(anchor="w")
        tk.Label(text_area, text="Practical Documentation Generator  ·  Python  C  C++",
                 font=("Consolas", 8),
                 bg=C["sidebar"], fg=C["muted"]).pack(anchor="w")

        # Right: Save / Load
        right = frm(inner_hdr, bg=C["sidebar"])
        right.pack(side="right")
        btn(right, "Load", self._load_session_manual,
            bg=C["card"], fg=C["text_dim"], px=12, py=5,
            hover=C["card_hover"]).pack(side="right", padx=(6, 0))
        btn(right, "Save", self._save_session_manual,
            bg=C["card"], fg=C["text_dim"], px=12, py=5,
            hover=C["card_hover"]).pack(side="right", padx=6)

        # Bottom border
        tk.Frame(hdr, bg=C["border"], height=1).pack(fill="x", side="bottom")

        # ── Body ─────────────────────────────────────────────────────────────
        body = frm(self)
        body.pack(fill="both", expand=True)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sb = frm(body, bg=C["sidebar"], width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        tk.Frame(sb, bg=C["border"], width=1).pack(side="right", fill="y")

        lbl(sb, "WORKSPACE", font=("Consolas", 8, "bold"),
            bg=C["sidebar"], fg=C["muted"]).pack(
            pady=(20, 8), padx=20, anchor="w")

        self._nav_btns = {}
        for icon, name, hint in NAV:
            f = frm(sb, bg=C["sidebar"])
            f.pack(fill="x")

            b = tk.Button(
                f, text=f"  {icon}  {name}",
                font=F_BODY, anchor="w",
                bg=C["sidebar"], fg=C["text_dim"],
                activebackground=C["card"],
                activeforeground=C["accent"],
                relief="flat", bd=0, padx=16, pady=11,
                cursor="hand2",
                command=lambda n=name: self._switch_tab(n))
            b.pack(fill="x")
            self._nav_btns[name] = b

        # Sidebar status block at bottom
        sep(sb).pack(fill="x", side="bottom", pady=0)
        sb_footer = frm(sb, bg=C["sidebar"])
        sb_footer.pack(side="bottom", fill="x", padx=16, pady=12)
        lbl(sb_footer, "v4.0  ·  AutoDocSystem",
            font=("Consolas", 8), fg=C["muted"],
            bg=C["sidebar"]).pack(anchor="w")

        # ── Content area ─────────────────────────────────────────────────────
        self._content = frm(body, bg=C["bg"])
        self._content.pack(side="left", fill="both", expand=True)
        self._pages = {}
        for _, name, _ in NAV:
            p = frm(self._content, bg=C["bg"])
            p.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._pages[name] = p

        self._build_setup(self._pages["Setup"])
        self._build_experiments(self._pages["Experiments"])
        self._build_log(self._pages["Log"])

        # ── Bottom action bar ─────────────────────────────────────────────────
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")
        bot = frm(self, bg=C["sidebar"], pady=0)
        bot.pack(fill="x", side="bottom")

        action_area = frm(bot, bg=C["sidebar"])
        action_area.pack(fill="x", padx=16, pady=10)

        self._gen_btn = btn(
            action_area, "▶  Generate Report",
            self._start_pipeline,
            bg=C["accent"], fg=C["bg"], px=20, py=8)
        self._gen_btn.pack(side="left")

        self._open_btn = btn(
            action_area, "Open Output",
            self._open_output,
            bg=C["card"], fg=C["text_dim"], px=16, py=8,
            hover=C["card_hover"])
        self._open_btn.pack(side="left", padx=10)
        self._open_btn.configure(state="disabled")

        self._status = tk.Label(
            action_area, text="Ready",
            font=F_SMALL, bg=C["sidebar"], fg=C["muted"])
        self._status.pack(side="left", padx=12)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Cyan.Horizontal.TProgressbar",
                        troughcolor=C["card"],
                        background=C["accent"],
                        bordercolor=C["border"],
                        lightcolor=C["accent2"],
                        darkcolor=C["accent_dim"])
        self._prog = ttk.Progressbar(
            action_area, mode="determinate", length=180,
            style="Cyan.Horizontal.TProgressbar")
        self._prog.pack(side="right")

    # ── Setup Tab ────────────────────────────────────────────────────────────

    def _build_setup(self, page):
        # Page header
        _page_header(page, "Setup", "Configure template, code folder, and output destination")

        pad = frm(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=32, pady=16)

        self._template_var = tk.StringVar()
        self._code_var     = tk.StringVar()
        self._out_var      = tk.StringVar()

        rows = [
            ("Template .docx",
             "Word file whose formatting will be copied for output",
             self._template_var, False, [("Word Documents", "*.docx")]),
            ("Code Folder",
             "Directory containing .py / .c / .cpp files  (Q1.c, exp2.py, 3.cpp …)",
             self._code_var, True, None),
            ("Output Folder",
             "Destination for the generated report (.docx)",
             self._out_var, True, None),
        ]

        for label, hint, var, is_folder, ftypes in rows:
            card = frm(pad, bg=C["card"])
            card.pack(fill="x", pady=5)

            # Left accent bar
            tk.Frame(card, bg=C["accent"], width=2).pack(side="left", fill="y")

            inner = frm(card, bg=C["card"])
            inner.pack(fill="x", padx=18, pady=12)

            row_top = frm(inner, bg=C["card"])
            row_top.pack(fill="x")

            lbl(row_top, label, font=F_BOLD,
                bg=C["card"], fg=C["text"]).pack(side="left")
            lbl(row_top, f"  —  {hint}",
                font=F_SMALL, fg=C["text_dim"], bg=C["card"]).pack(side="left")

            row_bot = frm(inner, bg=C["card"])
            row_bot.pack(fill="x", pady=(8, 0))

            ent = entry(row_bot, var, width=54)
            ent.pack(side="left", fill="x", expand=True)
            var.trace_add("write", lambda *_: self._autosave())

            pick = (lambda v=var: self._pick_folder(v)) if is_folder \
                   else (lambda v=var, ft=ftypes: self._pick_file(v, ft))
            btn(row_bot, "Browse", pick,
                bg=C["border"], fg=C["text_dim"], px=12, py=5,
                hover=C["card_hover"]).pack(side="left", padx=(8, 0))

        # ── Folder scanner ───────────────────────────────────────────────────
        sep(pad).pack(fill="x", pady=(20, 16))

        sc_hdr = frm(pad, bg=C["bg"])
        sc_hdr.pack(fill="x", pady=(0, 8))
        lbl(sc_hdr, "Code Folder Scanner", font=F_HEAD,
            fg=C["text"]).pack(side="left")
        btn(sc_hdr, "Scan & Match", self._scan_folder,
            bg=C["card"], fg=C["accent"], px=14, py=5,
            hover=C["card_hover"]).pack(side="right")

        sc_wrap = frm(pad, bg=C["card"])
        sc_wrap.pack(fill="x")
        tk.Frame(sc_wrap, bg=C["accent_dim"], width=2).pack(side="left", fill="y")

        self._scan_box = tk.Text(
            sc_wrap, font=F_MONO, bg=C["log_bg"], fg=C["log_text"],
            height=6, relief="flat", state="disabled",
            wrap="word", padx=14, pady=10)
        self._scan_box.pack(fill="x", expand=True)

        for tag, fg_ in [("ok",  C["success"]), ("warn", C["warn"]),
                          ("dim", C["muted"]),   ("head", C["accent"]),
                          ("err", C["err"])]:
            self._scan_box.tag_config(tag, foreground=fg_)

        lbl(pad,
            "After setup, go to Experiments to add or auto-detect practicals.",
            font=F_SMALL, fg=C["muted"]).pack(anchor="w", pady=(14, 0))

    # ── Experiments Tab ──────────────────────────────────────────────────────

    def _build_experiments(self, page):
        _page_header(page, "Experiments", "Add and manage practicals — each maps to a source file")

        pad = frm(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=32, pady=16)

        # Toolbar
        tb = frm(pad, bg=C["bg"])
        tb.pack(fill="x", pady=(0, 10))

        for text, cmd, bg_, fg_ in [
            ("Delete",      self._delete_selected, C["card"],   C["err"]),
            ("Edit",        self._edit_selected,   C["card"],   C["text_dim"]),
            ("Add",         self._add_experiment,  C["card"],   C["success"]),
            ("Auto-Detect", self._auto_detect,     C["accent"], C["bg"]),
        ]:
            btn(tb, text, cmd, bg=bg_, fg=fg_, px=14, py=6,
                hover=C["card_hover"]).pack(side="right", padx=4)

        # Import / Export
        ie = frm(pad, bg=C["bg"])
        ie.pack(fill="x", pady=(0, 10))
        lbl(ie, "Import / Export:", font=F_SMALL, fg=C["muted"]).pack(side="left")
        btn(ie, "Import questions.txt",
            self._import_txt, bg=C["card"], fg=C["text_dim"],
            px=12, py=4, hover=C["card_hover"]).pack(side="left", padx=8)
        btn(ie, "Export questions.txt",
            self._export_txt, bg=C["card"], fg=C["text_dim"],
            px=12, py=4, hover=C["card_hover"]).pack(side="left")

        sep(pad).pack(fill="x", pady=(0, 10))

        # ── Treeview ─────────────────────────────────────────────────────────
        style = ttk.Style()
        style.configure("Doc.Treeview",
                        background=C["card"],
                        foreground=C["text"],
                        fieldbackground=C["card"],
                        rowheight=32, font=F_BODY)
        style.configure("Doc.Treeview.Heading",
                        background=C["sidebar"],
                        foreground=C["text_dim"],
                        font=F_SMALL, relief="flat")
        style.map("Doc.Treeview",
                  background=[("selected", C["row_sel"])],
                  foreground=[("selected", C["accent"])])

        cols = ("No.", "Question / Aim", "Input (stdin)")
        tree_wrap = frm(pad, bg=C["bg"])
        tree_wrap.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(
            tree_wrap, columns=cols, show="headings",
            style="Doc.Treeview", selectmode="browse")
        self._tree.heading("No.",            text="No.",           anchor="center")
        self._tree.heading("Question / Aim", text="Question / Aim", anchor="w")
        self._tree.heading("Input (stdin)",  text="Input (stdin)", anchor="w")
        self._tree.column("No.",            width=50,  anchor="center", stretch=False)
        self._tree.column("Question / Aim", width=500, anchor="w")
        self._tree.column("Input (stdin)",  width=160, anchor="w")
        self._tree.tag_configure("alt", background=C["row_alt"])

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self._tree.bind("<Double-1>", lambda e: self._edit_selected())

        lbl(page,
            "Exp number must match filename  ·  EXP 1 → Q1.c / exp1.py / 1.cpp  ·  Double-click to edit",
            font=F_SMALL, fg=C["muted"]).pack(anchor="w", pady=(6, 4))

    # ── Log Tab ──────────────────────────────────────────────────────────────

    def _build_log(self, page):
        _page_header(page, "Log", "Pipeline execution output")

        hdr = frm(page, bg=C["bg"])
        hdr.pack(fill="x", padx=32, pady=(0, 4))
        btn(hdr, "Clear", self._clear_log,
            bg=C["card"], fg=C["text_dim"], px=10, py=4,
            hover=C["card_hover"]).pack(side="right")

        log_wrap = frm(page, bg=C["bg"])
        log_wrap.pack(fill="both", expand=True, padx=32, pady=(0, 16))

        # border frame
        border_frame = tk.Frame(log_wrap, bg=C["border"], padx=1, pady=1)
        border_frame.pack(fill="both", expand=True)

        self._log_w = tk.Text(
            border_frame, font=F_MONO, bg=C["log_bg"], fg=C["log_text"],
            relief="flat", state="disabled", wrap="word",
            insertbackground=C["accent"], pady=12, padx=14)
        vsb = ttk.Scrollbar(border_frame, orient="vertical", command=self._log_w.yview)
        self._log_w.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_w.pack(fill="both", expand=True)

        for tag, fg_ in [("INFO",   C["text_dim"]),  ("WARN",    C["warn"]),
                          ("ERROR",  C["err"]),       ("SUCCESS", C["success"]),
                          ("DIM",    C["muted"])]:
            self._log_w.tag_config(tag, foreground=fg_)

    # ── Navigation ───────────────────────────────────────────────────────────

    def _switch_tab(self, name: str):
        for n, b in self._nav_btns.items():
            if n == name:
                b.configure(bg=C["card"], fg=C["accent"])
                # Draw a left edge indicator by adding a tiny colored bar
            else:
                b.configure(bg=C["sidebar"], fg=C["text_dim"])
        self._pages[name].lift()

    # ── Folder Scanner ───────────────────────────────────────────────────────

    def _scan_folder(self):
        from app.modules.code_mapper import CodeMapper
        folder = self._code_var.get().strip()
        self._scan_box.configure(state="normal")
        self._scan_box.delete("1.0", "end")

        if not folder:
            self._scan_box.insert("end", "!  No code folder selected.\n", "warn")
            self._scan_box.configure(state="disabled")
            return

        p = Path(folder).resolve()
        if not p.exists():
            self._scan_box.insert("end", f"ERR  Folder not found:\n  {p}\n", "err")
            self._scan_box.configure(state="disabled")
            return

        mapper    = CodeMapper(p)
        all_files = mapper.all_files()
        self._scan_box.insert("end", f"PATH  {p}\n", "head")

        if not all_files:
            self._scan_box.insert("end",
                "!  No .py / .c / .cpp files found here.\n"
                "   Make sure you selected the right folder.\n", "warn")
        else:
            names = "  ".join(f.name for f in all_files)
            self._scan_box.insert("end", f"  {len(all_files)} file(s): ", "dim")
            self._scan_box.insert("end", names + "\n", "ok")

            if self._experiments:
                self._scan_box.insert("end", "\nMatch results:\n", "head")
                for exp in self._experiments:
                    no  = exp["exp_no"]
                    hit = mapper.find(no)
                    if hit:
                        self._scan_box.insert("end",
                            f"  [{no:>3}]  OK   {hit.name}\n", "ok")
                    else:
                        self._scan_box.insert("end",
                            f"  [{no:>3}]  MISS  expected: exp{no}.py / Q{no}.c / {no}.cpp\n",
                            "warn")
            else:
                self._scan_box.insert("end",
                    "\n  Add experiments (or Auto-Detect) to see matching.\n", "dim")

        self._scan_box.configure(state="disabled")

    # ── Auto-Detect ──────────────────────────────────────────────────────────

    def _auto_detect(self):
        from app.modules.code_mapper import CodeMapper
        folder = self._code_var.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("No folder",
                "Select a Code Folder in the Setup tab first.", parent=self)
            return

        mapper    = CodeMapper(Path(folder).resolve())
        all_files = mapper.all_files()
        if not all_files:
            messagebox.showinfo("No files",
                "No .py / .c / .cpp files found in the selected folder.", parent=self)
            return

        import re
        detected = []
        for f in all_files:
            m = re.search(r"(\d+)", f.stem)
            if m:
                detected.append(m.group(1))

        if not detected:
            messagebox.showinfo("No numbers found",
                "Could not extract experiment numbers from filenames.\n"
                "Expected names like Q1.c, exp2.py, 3.cpp …", parent=self)
            return

        seen    = {e["exp_no"] for e in self._experiments}
        new_nos = sorted(set(detected) - seen, key=lambda x: int(x) if x.isdigit() else x)

        if not new_nos:
            messagebox.showinfo("Up to date",
                "All detected experiment numbers are already in the list.", parent=self)
            return

        AutoDetectDialog(self, new_nos, all_files, on_confirm=self._on_autodetect_confirm)

    def _on_autodetect_confirm(self, entries: list[dict]):
        for e in entries:
            self._experiments.append(e)
        self._experiments.sort(key=lambda x: _sort_key(x["exp_no"]))
        self._refresh_tree()
        self._autosave()

    # ── Experiment CRUD ──────────────────────────────────────────────────────

    def _add_experiment(self):
        existing = {e["exp_no"] for e in self._experiments}
        next_no  = ""
        for i in range(1, 100):
            if str(i) not in existing:
                next_no = str(i)
                break
        ExpDialog(self, "Add Experiment", on_save=self._on_exp_saved, prefill_no=next_no)

    def _edit_selected(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select an experiment to edit.", parent=self)
            return
        idx = int(sel[0])
        ExpDialog(self, "Edit Experiment",
                  data=self._experiments[idx],
                  on_save=lambda d, i=idx: self._on_exp_edited(d, i))

    def _delete_selected(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        no  = self._experiments[idx]["exp_no"]
        if messagebox.askyesno("Delete", f"Delete Experiment {no}?", parent=self):
            self._experiments.pop(idx)
            self._refresh_tree()
            self._autosave()

    def _on_exp_saved(self, data):
        self._experiments.append(data)
        self._experiments.sort(key=lambda x: _sort_key(x["exp_no"]))
        self._refresh_tree()
        self._autosave()

    def _on_exp_edited(self, data, idx):
        self._experiments[idx] = data
        self._experiments.sort(key=lambda x: _sort_key(x["exp_no"]))
        self._refresh_tree()
        self._autosave()

    def _refresh_tree(self):
        self._tree.delete(*self._tree.get_children())
        for i, exp in enumerate(self._experiments):
            inp = exp["input"].replace("\n", " ↵ ")
            if len(inp) > 35:
                inp = inp[:35] + "…"
            self._tree.insert("", "end", iid=str(i),
                              tags=("alt",) if i % 2 else (),
                              values=(exp["exp_no"],
                                      exp["question"][:90],
                                      inp))

    # ── Import / Export txt ──────────────────────────────────────────────────

    def _import_txt(self):
        path = filedialog.askopenfilename(
            title="Select questions.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self)
        if not path:
            return
        try:
            from app.modules.question_parser import QuestionParser
            entries = QuestionParser(Path(path)).parse()
            inp_path = Path(path).parent / "inputs.txt"
            if inp_path.exists():
                QuestionParser(Path(path)).merge_inputs(entries, inp_path)

            if not entries:
                messagebox.showwarning("Empty", "No experiments found in that file.", parent=self)
                return

            if self._experiments:
                if not messagebox.askyesno("Replace?",
                        f"Found {len(entries)} experiment(s).\n"
                        "Replace current list? (No = append)", parent=self):
                    self._experiments.extend(entries)
                else:
                    self._experiments = entries
            else:
                self._experiments = entries

            self._experiments.sort(key=lambda x: _sort_key(x["exp_no"]))
            self._refresh_tree()
            self._autosave()
            messagebox.showinfo("Imported",
                                f"Imported {len(entries)} experiment(s).", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _export_txt(self):
        if not self._experiments:
            messagebox.showwarning("Empty", "No experiments to export.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Save as questions.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="questions.txt",
            parent=self)
        if not path:
            return
        lines = [
            "# AutoDocSystem — questions.txt\n"
            "# EXP: <number>   QUESTION: <aim>   INPUT: <stdin>\n"
        ]
        for exp in self._experiments:
            lines.append(f"EXP: {exp['exp_no']}")
            lines.append(f"QUESTION: {exp['question']}")
            lines.append(f"INPUT: {exp['input']}")
            lines.append("")
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        messagebox.showinfo("Exported", f"Saved to:\n{path}", parent=self)

    # ── Pipeline ─────────────────────────────────────────────────────────────

    def _validate(self):
        errs = []
        if not self._template_var.get():
            errs.append("• Template .docx required  (Setup tab)")
        elif not Path(self._template_var.get()).exists():
            errs.append("• Template .docx not found")
        if not self._code_var.get():
            errs.append("• Code folder required  (Setup tab)")
        elif not Path(self._code_var.get()).exists():
            errs.append("• Code folder not found")
        if not self._out_var.get():
            errs.append("• Output folder required  (Setup tab)")
        if not self._experiments:
            errs.append("• No experiments added  (Experiments tab)")
        return errs

    def _start_pipeline(self):
        if self._running:
            return
        errs = self._validate()
        if errs:
            messagebox.showerror("Missing inputs", "\n".join(errs), parent=self)
            return

        self._running = True
        self._gen_btn.configure(state="disabled", text="⏳  Running…")
        self._open_btn.configure(state="disabled")
        self._prog["value"] = 0
        self._clear_log()
        self._switch_tab("Log")

        cfg = {
            "template"   : self._template_var.get(),
            "experiments": self._experiments,
            "code_dir"   : self._code_var.get(),
            "out_dir"    : self._out_var.get(),
        }
        threading.Thread(target=self._run_bg, args=(cfg,), daemon=True).start()

    def _run_bg(self, cfg):
        try:
            Pipeline(cfg, self._queue).run()
        except Exception as e:
            self._queue.put(("ERROR", str(e)))
        finally:
            self._queue.put(("DONE", None))

    # ── Queue poll ───────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                kind, data = self._queue.get_nowait()
                if kind == "LOG":
                    lvl, msg = data
                    self._log_w.configure(state="normal")
                    self._log_w.insert("end", msg + "\n", lvl)
                    self._log_w.see("end")
                    self._log_w.configure(state="disabled")
                elif kind == "PROGRESS":
                    done, total = data
                    self._prog["maximum"] = max(total, 1)
                    self._prog["value"]   = done
                    self._status.configure(text=f"Experiment {done} / {total}")
                elif kind == "STATUS":
                    self._status.configure(text=data)
                elif kind == "DONE":
                    self._on_done()
                elif kind == "ERROR":
                    self._log_w.configure(state="normal")
                    self._log_w.insert("end", f"[FATAL] {data}\n", "ERROR")
                    self._log_w.see("end")
                    self._log_w.configure(state="disabled")
                    self._on_done(ok=False)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _on_done(self, ok=True):
        self._running = False
        self._gen_btn.configure(state="normal", text="▶  Generate Report")
        self._open_btn.configure(state="normal")
        self._status.configure(
            text="Done" if ok else "Failed — see log")

    def _clear_log(self):
        self._log_w.configure(state="normal")
        self._log_w.delete("1.0", "end")
        self._log_w.configure(state="disabled")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _pick_file(self, var, ftypes):
        p = filedialog.askopenfilename(filetypes=ftypes or [], parent=self)
        if p: var.set(p)

    def _pick_folder(self, var):
        p = filedialog.askdirectory(parent=self)
        if p: var.set(p)

    def _open_output(self):
        folder = self._out_var.get()
        if folder and Path(folder).exists():
            import subprocess, sys as _sys
            if _sys.platform == "win32":
                subprocess.Popen(["explorer", folder])
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    # ── Session ──────────────────────────────────────────────────────────────

    def _autosave(self):
        save_session({
            "template"   : self._template_var.get(),
            "code_dir"   : self._code_var.get(),
            "out_dir"    : self._out_var.get(),
            "experiments": self._experiments,
        })

    def _load_session(self):
        data = load_session()
        if data.get("template"):    self._template_var.set(data["template"])
        if data.get("code_dir"):    self._code_var.set(data["code_dir"])
        if data.get("out_dir"):     self._out_var.set(data["out_dir"])
        if data.get("experiments"):
            self._experiments = data["experiments"]
            self._refresh_tree()

    def _save_session_manual(self):
        self._autosave()
        messagebox.showinfo("Saved", f"Session saved to:\n{SESSION_FILE}", parent=self)

    def _load_session_manual(self):
        path = filedialog.askopenfilename(
            title="Load session file",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
            parent=self)
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if data.get("template"):    self._template_var.set(data["template"])
            if data.get("code_dir"):    self._code_var.set(data["code_dir"])
            if data.get("out_dir"):     self._out_var.set(data["out_dir"])
            if data.get("experiments"):
                self._experiments = data["experiments"]
                self._refresh_tree()
            messagebox.showinfo("Loaded",
                                f"Loaded {len(self._experiments)} experiment(s).", parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _on_close(self):
        self._autosave()
        self.destroy()


# ── Page header helper ───────────────────────────────────────────────────────

def _page_header(page, title: str, subtitle: str):
    hdr = frm(page, bg=C["sidebar"])
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=C["border"], height=1).pack(fill="x", side="bottom")
    inner = frm(hdr, bg=C["sidebar"])
    inner.pack(fill="x", padx=32, pady=14)
    lbl(inner, title, font=F_TITLE, bg=C["sidebar"], fg=C["text"]).pack(side="left")
    lbl(inner, f"  —  {subtitle}", font=F_SMALL,
        bg=C["sidebar"], fg=C["muted"]).pack(side="left", pady=(2, 0))


# ── Auto-Detect Confirmation Dialog ──────────────────────────────────────────

class AutoDetectDialog(tk.Toplevel):
    def __init__(self, parent, nos: list[str], all_files, on_confirm):
        super().__init__(parent)
        self.title("Auto-Detect Experiments")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.geometry("700x520")
        self.grab_set()
        self._on_confirm = on_confirm
        self._rows: list[dict] = []

        # Dialog header
        dh = frm(self, bg=C["sidebar"])
        dh.pack(fill="x")
        tk.Frame(dh, bg=C["accent"], height=2).pack(fill="x", side="top")
        tk.Frame(dh, bg=C["border"], height=1).pack(fill="x", side="bottom")
        dhi = frm(dh, bg=C["sidebar"])
        dhi.pack(fill="x", padx=24, pady=12)
        lbl(dhi, f"Auto-Detect  ·  {len(nos)} new experiment(s) found",
            font=F_TITLE, bg=C["sidebar"], fg=C["text"]).pack(side="left")

        pad = frm(self, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=12)

        lbl(pad, "Fill in the Question/Aim for each. Input (stdin) is optional.",
            font=F_SMALL, fg=C["muted"]).pack(anchor="w", pady=(0, 12))

        canvas = tk.Canvas(pad, bg=C["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(pad, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = frm(canvas, bg=C["bg"])
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")

        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for no in nos:
            from app.modules.code_mapper import CodeMapper
            hit  = CodeMapper(all_files[0].parent).find(no)
            hint = f"→ {hit.name}" if hit else "→ no file matched"

            row_frm = frm(inner, bg=C["card"])
            row_frm.pack(fill="x", pady=4)
            tk.Frame(row_frm, bg=C["accent"], width=2).pack(side="left", fill="y")

            ri = frm(row_frm, bg=C["card"])
            ri.pack(fill="x", padx=16, pady=10)

            lbl(ri, f"Exp {no}", font=F_BOLD, bg=C["card"], fg=C["accent"]).grid(
                row=0, column=0, sticky="nw", pady=(0, 4))
            lbl(ri, hint, font=F_SMALL, fg=C["success"] if hit else C["warn"],
                bg=C["card"]).grid(row=1, column=0, sticky="w")

            q_var = tk.StringVar()
            entry(ri, q_var, width=46).grid(row=0, column=1, padx=(12, 0), sticky="ew")
            lbl(ri, "Question / Aim", font=F_SMALL,
                fg=C["muted"], bg=C["card"]).grid(row=1, column=1, padx=(12, 0), sticky="w")

            in_var = tk.StringVar()
            entry(ri, in_var, width=18).grid(row=0, column=2, padx=(10, 0), sticky="ew")
            lbl(ri, "Input (stdin)", font=F_SMALL,
                fg=C["muted"], bg=C["card"]).grid(row=1, column=2, padx=(10, 0), sticky="w")

            ri.columnconfigure(1, weight=1)
            self._rows.append({"no": no, "q": q_var, "inp": in_var})

        bot = frm(self, bg=C["sidebar"])
        bot.pack(fill="x", side="bottom")
        tk.Frame(bot, bg=C["border"], height=1).pack(fill="x", side="top")
        bot_inner = frm(bot, bg=C["sidebar"])
        bot_inner.pack(fill="x", padx=24, pady=10)
        btn(bot_inner, "Cancel", self.destroy,
            bg=C["card"], fg=C["text_dim"], px=16, py=6,
            hover=C["card_hover"]).pack(side="left")
        btn(bot_inner, "Add All", self._confirm,
            bg=C["accent"], fg=C["bg"], px=20, py=6).pack(side="right")

    def _confirm(self):
        entries = []
        for r in self._rows:
            entries.append({
                "exp_no"  : r["no"],
                "question": r["q"].get().strip() or f"Experiment {r['no']}",
                "input"   : r["inp"].get().strip(),
            })
        self._on_confirm(entries)
        self.destroy()


# ── Add / Edit Dialog ─────────────────────────────────────────────────────────

class ExpDialog(tk.Toplevel):
    def __init__(self, parent, title, on_save, data=None, prefill_no=""):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._on_save  = on_save
        self._code_dir = getattr(parent, "_code_var", None)

        # Dialog header
        dh = frm(self, bg=C["sidebar"])
        dh.pack(fill="x")
        tk.Frame(dh, bg=C["accent"], height=2).pack(fill="x", side="top")
        tk.Frame(dh, bg=C["border"], height=1).pack(fill="x", side="bottom")
        dhi = frm(dh, bg=C["sidebar"])
        dhi.pack(fill="x", padx=28, pady=12)
        lbl(dhi, title, font=F_TITLE, bg=C["sidebar"], fg=C["text"]).pack(side="left")

        pad = frm(self, bg=C["bg"])
        pad.pack(padx=28, pady=18, fill="both")

        # ── Experiment number ────────────────────────────────────────────────
        lbl(pad, "Experiment No.", font=F_SMALL, fg=C["muted"]).grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        no_frm = frm(pad, bg=C["bg"])
        no_frm.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=(0, 4))

        self._no = tk.StringVar(value=data["exp_no"] if data else prefill_no)
        eno = entry(no_frm, self._no, width=10)
        eno.pack(side="left")

        self._match_lbl = lbl(no_frm,
            "  enter a number to check file match",
            font=F_SMALL, fg=C["muted"], bg=C["bg"])
        self._match_lbl.pack(side="left", padx=(10, 0))
        self._no.trace_add("write", lambda *_: self._update_match())

        sep(pad).grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)

        # ── Question ─────────────────────────────────────────────────────────
        lbl(pad, "Question / Aim", font=F_SMALL, fg=C["muted"]).grid(
            row=2, column=0, sticky="nw", pady=6)
        self._q = textbox(pad, font=F_BODY, height=4, width=56)
        self._q.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=6)
        if data:
            self._q.insert("1.0", data["question"])

        # ── Input ────────────────────────────────────────────────────────────
        lbl(pad, "Input (stdin)", font=F_SMALL, fg=C["muted"]).grid(
            row=3, column=0, sticky="nw", pady=6)
        lbl(pad,
            "One value per\nline — piped to\nstdin on run.\n\nLeave blank\nif none needed.",
            font=F_SMALL, fg=C["muted"]).grid(row=4, column=0, sticky="nw")

        self._inp = textbox(pad, height=6, width=56)
        self._inp.grid(row=3, column=1, rowspan=2, sticky="ew", padx=(12, 0), pady=6)
        if data:
            self._inp.insert("1.0", data["input"])

        # ── Preview ──────────────────────────────────────────────────────────
        lbl(pad, "Stdin preview", font=F_SMALL, fg=C["muted"]).grid(
            row=5, column=0, sticky="nw", pady=(10, 0))
        self._preview = tk.Text(
            pad, font=F_MONO_B, bg=C["log_bg"], fg=C["success"],
            height=4, relief="flat", state="disabled",
            highlightbackground=C["border"], highlightthickness=1,
            width=56, padx=12, pady=8)
        self._preview.grid(row=5, column=1, sticky="ew", padx=(12, 0), pady=(10, 0))
        self._inp.bind("<KeyRelease>", lambda e: self._update_preview())
        self._update_preview()

        lbl(pad, "Each line above becomes one stdin entry.",
            font=F_SMALL, fg=C["muted"]).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # ── Buttons ──────────────────────────────────────────────────────────
        sep(pad).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        brow = frm(pad, bg=C["bg"])
        brow.grid(row=8, column=0, columnspan=2, pady=(12, 0), sticky="e")
        btn(brow, "Cancel", self.destroy,
            bg=C["card"], fg=C["text_dim"], px=16, py=6,
            hover=C["card_hover"]).pack(side="left", padx=(0, 8))
        btn(brow, "Save", self._save,
            bg=C["accent"], fg=C["bg"], px=20, py=6).pack(side="left")

        pad.columnconfigure(1, weight=1)
        self._update_match()

    def _update_match(self):
        no = self._no.get().strip()
        if not no:
            self._match_lbl.configure(text="  enter a number", fg=C["muted"])
            return
        code_dir = self._code_dir.get().strip() if self._code_dir else None
        if not code_dir or not Path(code_dir).exists():
            self._match_lbl.configure(
                text="  (set Code Folder in Setup first)", fg=C["muted"])
            return
        from app.modules.code_mapper import CodeMapper
        hit = CodeMapper(Path(code_dir).resolve()).find(no)
        if hit:
            self._match_lbl.configure(
                text=f"  ✓  matches:  {hit.name}", fg=C["success"])
        else:
            self._match_lbl.configure(
                text=f"  ✗  no match found for '{no}'",
                fg=C["err"])

    def _update_preview(self):
        raw   = self._inp.get("1.0", "end").rstrip("\n")
        lines = raw.splitlines() if raw.strip() else ["(no input)"]
        text  = "\n".join(f"  [{i}]  {ln}" for i, ln in enumerate(lines))
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.insert("1.0", text)
        self._preview.configure(state="disabled")

    def _save(self):
        no  = self._no.get().strip()
        q   = self._q.get("1.0", "end").strip()
        inp = self._inp.get("1.0", "end").rstrip("\n")
        if not no:
            messagebox.showerror("Error", "Experiment number required.", parent=self)
            return
        if not q:
            messagebox.showerror("Error", "Question / Aim required.", parent=self)
            return
        self._on_save({"exp_no": no, "question": q, "input": inp})
        self.destroy()


def _sort_key(exp_no):
    try:    return (0, int(exp_no))
    except: return (1, exp_no)


def launch():
    App().mainloop()