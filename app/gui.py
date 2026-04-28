"""
app/gui.py  —  AutoDocSystem  v4

Tabs:
  ⚙  Setup       — template, code folder, output folder + live folder scanner
  📋 Experiments  — built-in editor with auto-detect, import/export
  📄 Log          — dark terminal + progress

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

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg"      : "#1A1A2E",
    "sidebar" : "#16213E",
    "card"    : "#0F3460",
    "accent"  : "#E94560",
    "accent2" : "#533483",
    "success" : "#00B4D8",
    "ok"      : "#06D6A0",
    "warn"    : "#FFD166",
    "err"     : "#EF476F",
    "text"    : "#EAEAEA",
    "muted"   : "#8892A4",
    "entry"   : "#1E2A45",
    "border"  : "#2D3F6B",
    "log_bg"  : "#0D1117",
    "log_text": "#8B949E",
    "row_alt" : "#162032",
    "row_sel" : "#533483",
}
F_BODY  = ("Segoe UI", 10)
F_BOLD  = ("Segoe UI", 10, "bold")
F_TITLE = ("Segoe UI", 13, "bold")
F_SMALL = ("Segoe UI", 9)
F_MONO  = ("Consolas", 9)
F_MONO_B= ("Consolas", 9, "bold")

NAV = [
    ("⚙",  "Setup",       "Configure paths"),
    ("📋", "Experiments", "Add your practicals"),
    ("📄", "Log",         "Run & view output"),
]

SESSION_FILE = Path(__file__).parent.parent / "session.json"


# ── Small widget helpers ──────────────────────────────────────────────────────

def btn(parent, text, cmd, bg=None, fg=None, font=None, px=14, py=7):
    return tk.Button(parent, text=text, command=cmd,
                     font=font or F_BOLD,
                     bg=bg or C["accent"], fg=fg or C["text"],
                     activebackground=C["accent2"], activeforeground=C["text"],
                     relief="flat", padx=px, pady=py, cursor="hand2", bd=0)

def lbl(parent, text, font=None, fg=None, bg=None, **kw):
    return tk.Label(parent, text=text, font=font or F_BODY,
                    fg=fg or C["text"], bg=bg or C["bg"], **kw)

def entry(parent, var, width=40):
    return tk.Entry(parent, textvariable=var, font=F_BODY,
                    bg=C["entry"], fg=C["text"], insertbackground=C["text"],
                    relief="flat", highlightbackground=C["border"],
                    highlightthickness=1, width=width)

def frm(parent, bg=None, **kw):
    return tk.Frame(parent, bg=bg or C["bg"], **kw)

def sep(parent):
    return tk.Frame(parent, bg=C["border"], height=1)

def textbox(parent, font=None, height=5, **kw):
    return tk.Text(parent, font=font or F_MONO,
                   bg=C["entry"], fg=C["text"],
                   insertbackground=C["text"],
                   relief="flat",
                   highlightbackground=C["border"],
                   highlightthickness=1,
                   height=height, **kw)


# ── Session persistence ───────────────────────────────────────────────────────

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
            encoding="utf-8"
        )
    except Exception:
        pass


# ── Main App ──────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoDocSystem  —  Practical Documentation Generator")
        self.geometry("1020x700")
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

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ──────────────────────────────────────────────────────────
        hdr = frm(self, bg=C["sidebar"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="  📄  AutoDocSystem",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["sidebar"], fg=C["accent"]).pack(side="left", pady=9)
        tk.Label(hdr, text="Practical Documentation Generator  ·  Python / C / C++",
                 font=F_SMALL, bg=C["sidebar"], fg=C["muted"]).pack(side="left", padx=10)

        # Save / Load session buttons in header
        btn(hdr, "💾 Save Session", self._save_session_manual,
            bg=C["card"], px=10, py=4).pack(side="right", padx=6, pady=6)
        btn(hdr, "📂 Load Session", self._load_session_manual,
            bg=C["card"], px=10, py=4).pack(side="right", padx=2, pady=6)

        # ── Body ─────────────────────────────────────────────────────────────
        body = frm(self)
        body.pack(fill="both", expand=True)

        # Sidebar
        sb = frm(body, bg=C["sidebar"], width=175)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        tk.Label(sb, text="NAVIGATION", font=("Segoe UI", 8, "bold"),
                 bg=C["sidebar"], fg=C["muted"]).pack(pady=(20, 6), padx=16, anchor="w")

        self._nav_btns = {}
        for icon, name, hint in NAV:
            f = frm(sb, bg=C["sidebar"])
            f.pack(fill="x", padx=8, pady=2)
            b = tk.Button(f, text=f"  {icon}  {name}",
                          font=F_BOLD, anchor="w",
                          bg=C["sidebar"], fg=C["text"],
                          activebackground=C["card"],
                          relief="flat", bd=0, padx=6, pady=9,
                          cursor="hand2",
                          command=lambda n=name: self._switch_tab(n))
            b.pack(fill="x")
            tk.Label(f, text=f"    {hint}",
                     font=("Segoe UI", 8),
                     bg=C["sidebar"], fg=C["muted"]).pack(anchor="w")
            self._nav_btns[name] = b

        # Version tag at bottom of sidebar
        tk.Label(sb, text="v4.0", font=("Segoe UI", 8),
                 bg=C["sidebar"], fg=C["border"]).pack(side="bottom", pady=8)

        # Content
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

        # ── Bottom bar ───────────────────────────────────────────────────────
        bot = frm(self, bg=C["sidebar"], pady=8)
        bot.pack(fill="x", side="bottom")

        self._gen_btn = btn(bot, "🚀  Generate Report",
                            self._start_pipeline,
                            bg=C["accent"], px=22, py=9)
        self._gen_btn.pack(side="left", padx=14)

        self._open_btn = btn(bot, "📁  Open Output Folder",
                             self._open_output,
                             bg=C["card"], px=14, py=9)
        self._open_btn.pack(side="left", padx=4)
        self._open_btn.configure(state="disabled")

        self._status = tk.Label(bot, text="Ready",
                                font=F_SMALL, bg=C["sidebar"], fg=C["muted"])
        self._status.pack(side="left", padx=14)

        self._prog = ttk.Progressbar(bot, mode="determinate", length=200)
        self._prog.pack(side="right", padx=14)

    # ── Setup Tab ─────────────────────────────────────────────────────────────

    def _build_setup(self, page):
        pad = frm(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=28, pady=18)

        lbl(pad, "Configuration", font=F_TITLE).pack(anchor="w")
        lbl(pad, "Paths are auto-saved and restored next time you open the app.",
            font=F_SMALL, fg=C["muted"]).pack(anchor="w", pady=(2, 16))

        self._template_var = tk.StringVar()
        self._code_var     = tk.StringVar()
        self._out_var      = tk.StringVar()

        rows = [
            ("📄  Template .docx",
             "Your previous experiment Word file — formatting is copied from it",
             self._template_var, False, [("Word Documents", "*.docx")]),
            ("📂  Code Folder",
             "Folder with .py / .c / .cpp files  (Q1.c, exp2.py, 3.cpp …)",
             self._code_var, True, None),
            ("💾  Output Folder",
             "Where the generated report (.docx) will be saved",
             self._out_var, True, None),
        ]

        for label, hint, var, is_folder, ftypes in rows:
            card = frm(pad, bg=C["card"])
            card.pack(fill="x", pady=4)
            inner = frm(card, bg=C["card"])
            inner.pack(fill="x", padx=14, pady=10)
            lbl(inner, label, font=F_BOLD, bg=C["card"]).grid(
                row=0, column=0, sticky="w")
            lbl(inner, hint, font=F_SMALL, fg=C["muted"], bg=C["card"]).grid(
                row=1, column=0, sticky="w")
            ent = entry(inner, var, width=48)
            ent.grid(row=0, column=1, rowspan=2, padx=(12, 8), sticky="ew")
            # auto-save on any change
            var.trace_add("write", lambda *_: self._autosave())
            pick = (lambda v=var: self._pick_folder(v)) if is_folder \
                   else (lambda v=var, ft=ftypes: self._pick_file(v, ft))
            btn(inner, "Browse", pick, bg=C["accent2"], px=10, py=5).grid(
                row=0, column=2, rowspan=2)
            inner.columnconfigure(1, weight=1)

        # ── Folder scanner ───────────────────────────────────────────────────
        sc = frm(pad, bg=C["card"])
        sc.pack(fill="x", pady=(12, 0))

        sh = frm(sc, bg=C["card"])
        sh.pack(fill="x", padx=14, pady=(8, 4))
        lbl(sh, "🔍  Code Folder Scanner", font=F_BOLD, bg=C["card"]).pack(side="left")
        btn(sh, "Scan & Match", self._scan_folder,
            bg=C["success"], fg=C["bg"], px=10, py=4).pack(side="right")

        self._scan_box = tk.Text(
            sc, font=F_MONO, bg=C["log_bg"], fg=C["log_text"],
            height=7, relief="flat", state="disabled",
            wrap="word", padx=10, pady=6)
        self._scan_box.pack(fill="x")
        for tag, fg_ in [("ok","#3FB950"),("warn","#E3B341"),
                          ("dim","#8B949E"),("head","#58A6FF"),
                          ("err","#F85149")]:
            self._scan_box.tag_config(tag, foreground=fg_)

        lbl(pad,
            "💡 After setup, go to  📋 Experiments  to add or auto-detect practicals.",
            font=F_SMALL, fg=C["warn"]).pack(anchor="w", pady=(10, 0))

    # ── Experiments Tab ───────────────────────────────────────────────────────

    def _build_experiments(self, page):
        pad = frm(page, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=28, pady=18)

        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = frm(pad, bg=C["bg"])
        tb.pack(fill="x", pady=(0, 10))
        lbl(tb, "Experiments", font=F_TITLE).pack(side="left")

        # Right-side buttons
        for text, cmd, bg_ in [
            ("🗑 Delete",      self._delete_selected, C["err"]),
            ("✏ Edit",         self._edit_selected,   C["accent2"]),
            ("+ Add",          self._add_experiment,  C["ok"]),
            ("⚡ Auto-Detect", self._auto_detect,     C["accent"]),
        ]:
            btn(tb, text, cmd, bg=bg_, px=11, py=5).pack(side="right", padx=3)

        # Import / Export row
        ie = frm(pad, bg=C["bg"])
        ie.pack(fill="x", pady=(0, 8))
        lbl(ie, "Import / Export:", font=F_SMALL, fg=C["muted"]).pack(side="left")
        btn(ie, "⬇ Import from questions.txt",
            self._import_txt, bg=C["card"], px=10, py=3).pack(side="left", padx=6)
        btn(ie, "⬆ Export to questions.txt",
            self._export_txt, bg=C["card"], px=10, py=3).pack(side="left")

        sep(pad).pack(fill="x", pady=(0, 8))

        # ── Treeview ─────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Treeview",
                        background=C["entry"], foreground=C["text"],
                        fieldbackground=C["entry"], rowheight=30, font=F_BODY)
        style.configure("Dark.Treeview.Heading",
                        background=C["card"], foreground=C["text"],
                        font=F_BOLD, relief="flat")
        style.map("Dark.Treeview",
                  background=[("selected", C["row_sel"])],
                  foreground=[("selected", C["text"])])

        cols = ("No.", "Question / Aim", "Input (stdin)")
        self._tree = ttk.Treeview(pad, columns=cols, show="headings",
                                   style="Dark.Treeview", selectmode="browse")
        self._tree.heading("No.",            text="No.",  anchor="center")
        self._tree.heading("Question / Aim", text="Question / Aim", anchor="w")
        self._tree.heading("Input (stdin)",  text="Input (stdin)",  anchor="w")
        self._tree.column("No.",            width=55,  anchor="center", stretch=False)
        self._tree.column("Question / Aim", width=460, anchor="w")
        self._tree.column("Input (stdin)",  width=180, anchor="w")
        self._tree.tag_configure("alt", background=C["row_alt"])

        vsb = ttk.Scrollbar(pad, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self._tree.bind("<Double-1>", lambda e: self._edit_selected())

        lbl(page,
            "💡 Exp number must match filename:  EXP 1 → Q1.c / exp1.py / 1.cpp   "
            "· Double-click a row to edit",
            font=F_SMALL, fg=C["muted"]).pack(anchor="w", padx=28, pady=(4, 8))

    # ── Log Tab ───────────────────────────────────────────────────────────────

    def _build_log(self, page):
        hdr = frm(page, bg=C["sidebar"], pady=6)
        hdr.pack(fill="x")
        lbl(hdr, "  📋  Run Log", font=F_BOLD, bg=C["sidebar"],
            fg=C["success"]).pack(side="left")
        btn(hdr, "Clear", self._clear_log,
            bg=C["sidebar"], fg=C["muted"], px=8, py=3).pack(side="right", padx=6)

        self._log_w = tk.Text(
            page, font=F_MONO, bg=C["log_bg"], fg=C["log_text"],
            relief="flat", state="disabled", wrap="word",
            insertbackground=C["text"], pady=8, padx=10)
        vsb = ttk.Scrollbar(page, orient="vertical", command=self._log_w.yview)
        self._log_w.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_w.pack(fill="both", expand=True)

        for tag, fg_ in [("INFO","#58A6FF"),("WARN","#E3B341"),
                          ("ERROR","#F85149"),("SUCCESS","#3FB950"),
                          ("DIM","#8B949E")]:
            self._log_w.tag_config(tag, foreground=fg_)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _switch_tab(self, name: str):
        for n, b in self._nav_btns.items():
            b.configure(bg=C["accent"] if n == name else C["sidebar"],
                        fg="white"     if n == name else C["text"])
        self._pages[name].lift()

    # ── Folder Scanner ────────────────────────────────────────────────────────

    def _scan_folder(self):
        from app.modules.code_mapper import CodeMapper
        folder = self._code_var.get().strip()
        self._scan_box.configure(state="normal")
        self._scan_box.delete("1.0", "end")

        if not folder:
            self._scan_box.insert("end", "⚠  No code folder selected.\n", "warn")
            self._scan_box.configure(state="disabled")
            return

        p = Path(folder).resolve()
        if not p.exists():
            self._scan_box.insert("end", f"⚠  Folder not found:\n  {p}\n", "err")
            self._scan_box.configure(state="disabled")
            return

        mapper    = CodeMapper(p)
        all_files = mapper.all_files()
        self._scan_box.insert("end", f"📂  {p}\n", "head")

        if not all_files:
            self._scan_box.insert("end",
                "⚠  No .py / .c / .cpp files found here.\n"
                "   → Make sure you selected the right folder.\n", "warn")
        else:
            names = "  ".join(f.name for f in all_files)
            self._scan_box.insert("end", f"Found {len(all_files)} file(s): ", "dim")
            self._scan_box.insert("end", names + "\n", "ok")

            if self._experiments:
                self._scan_box.insert("end", "\nExperiment → File matching:\n", "head")
                for exp in self._experiments:
                    no  = exp["exp_no"]
                    hit = mapper.find(no)
                    if hit:
                        self._scan_box.insert("end",
                            f"  Exp {no:>3}  ✓  {hit.name}\n", "ok")
                    else:
                        self._scan_box.insert("end",
                            f"  Exp {no:>3}  ✗  NOT FOUND"
                            f"  (expected: exp{no}.py / Q{no}.c / {no}.cpp)\n",
                            "warn")
            else:
                self._scan_box.insert("end",
                    "\n💡 Add experiments (or click ⚡ Auto-Detect) to see matching.\n", "dim")

        self._scan_box.configure(state="disabled")

    # ── Auto-Detect Experiments from folder ───────────────────────────────────

    def _auto_detect(self):
        from app.modules.code_mapper import CodeMapper
        folder = self._code_var.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showwarning(
                "No folder",
                "Select a Code Folder in the Setup tab first.",
                parent=self)
            return

        mapper    = CodeMapper(Path(folder).resolve())
        all_files = mapper.all_files()
        if not all_files:
            messagebox.showinfo(
                "No files",
                "No .py / .c / .cpp files found in the selected folder.",
                parent=self)
            return

        # Extract numbers from filenames
        import re
        detected = []
        for f in all_files:
            m = re.search(r"(\d+)", f.stem)
            if m:
                detected.append(m.group(1))

        if not detected:
            messagebox.showinfo(
                "No numbers found",
                "Could not extract experiment numbers from filenames.\n"
                "Expected names like Q1.c, exp2.py, 3.cpp …",
                parent=self)
            return

        # Remove duplicates, sort
        seen    = {e["exp_no"] for e in self._experiments}
        new_nos = sorted(set(detected) - seen, key=lambda x: int(x) if x.isdigit() else x)

        if not new_nos:
            messagebox.showinfo(
                "Up to date",
                "All detected experiment numbers are already in the list.",
                parent=self)
            return

        # Open a confirmation dialog listing what will be added
        AutoDetectDialog(self, new_nos, all_files, on_confirm=self._on_autodetect_confirm)

    def _on_autodetect_confirm(self, entries: list[dict]):
        for e in entries:
            self._experiments.append(e)
        self._experiments.sort(key=lambda x: _sort_key(x["exp_no"]))
        self._refresh_tree()
        self._autosave()

    # ── Experiment CRUD ───────────────────────────────────────────────────────

    def _add_experiment(self):
        # Pre-fill exp_no with next number
        existing = {e["exp_no"] for e in self._experiments}
        next_no  = ""
        for i in range(1, 100):
            if str(i) not in existing:
                next_no = str(i)
                break
        ExpDialog(self, "Add Experiment",
                  on_save=self._on_exp_saved,
                  prefill_no=next_no)

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

    # ── Import / Export txt ───────────────────────────────────────────────────

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
            # merge inputs.txt if present
            inp_path = Path(path).parent / "inputs.txt"
            if inp_path.exists():
                QuestionParser(Path(path)).merge_inputs(entries, inp_path)

            if not entries:
                messagebox.showwarning("Empty", "No experiments found in that file.", parent=self)
                return

            if self._experiments:
                if not messagebox.askyesno(
                        "Replace?",
                        f"Found {len(entries)} experiment(s).\n"
                        "Replace current list? (No = append)",
                        parent=self):
                    self._experiments.extend(entries)
                else:
                    self._experiments = entries
            else:
                self._experiments = entries

            self._experiments.sort(key=lambda x: _sort_key(x["exp_no"]))
            self._refresh_tree()
            self._autosave()
            messagebox.showinfo("Imported",
                                f"Imported {len(entries)} experiment(s).",
                                parent=self)
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

    # ── Pipeline ──────────────────────────────────────────────────────────────

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

    # ── Queue poll ────────────────────────────────────────────────────────────

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
        self._gen_btn.configure(state="normal", text="🚀  Generate Report")
        self._open_btn.configure(state="normal")
        self._status.configure(
            text="✅  Done!" if ok else "❌  Failed — see log")

    def _clear_log(self):
        self._log_w.configure(state="normal")
        self._log_w.delete("1.0", "end")
        self._log_w.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────

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

    # ── Session ───────────────────────────────────────────────────────────────

    def _autosave(self):
        save_session({
            "template"    : self._template_var.get(),
            "code_dir"    : self._code_var.get(),
            "out_dir"     : self._out_var.get(),
            "experiments" : self._experiments,
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
                                f"Loaded {len(self._experiments)} experiment(s).",
                                parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _on_close(self):
        self._autosave()
        self.destroy()


# ── Auto-Detect Confirmation Dialog ──────────────────────────────────────────

class AutoDetectDialog(tk.Toplevel):
    """Shows detected exp numbers, lets user fill questions before adding."""

    def __init__(self, parent, nos: list[str], all_files, on_confirm):
        super().__init__(parent)
        self.title("⚡ Auto-Detect Experiments")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.geometry("620x480")
        self.grab_set()
        self._on_confirm = on_confirm
        self._rows: list[dict] = []   # {no, q_var, in_var}

        pad = frm(self, bg=C["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=14)

        lbl(pad, f"Detected {len(nos)} new experiment number(s)",
            font=F_BOLD).pack(anchor="w")
        lbl(pad,
            "Fill in the Question/Aim for each. Input is optional.",
            font=F_SMALL, fg=C["muted"]).pack(anchor="w", pady=(2, 10))

        # Scrollable inner area
        canvas  = tk.Canvas(pad, bg=C["bg"], highlightthickness=0)
        vsb     = ttk.Scrollbar(pad, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = frm(canvas, bg=C["bg"])
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Build one row per detected number
        for no in nos:
            # Find matching file for hint
            from app.modules.code_mapper import CodeMapper
            hit = CodeMapper(all_files[0].parent).find(no)
            hint = f"→ {hit.name}" if hit else "→ file not matched yet"

            row_frm = frm(inner, bg=C["card"])
            row_frm.pack(fill="x", pady=4, padx=2)
            ri = frm(row_frm, bg=C["card"])
            ri.pack(fill="x", padx=10, pady=8)

            lbl(ri, f"Exp {no}", font=F_BOLD, bg=C["card"]).grid(
                row=0, column=0, sticky="nw", pady=2)
            lbl(ri, hint, font=F_SMALL, fg=C["ok"], bg=C["card"]).grid(
                row=1, column=0, sticky="w")

            q_var = tk.StringVar()
            entry(ri, q_var, width=44).grid(
                row=0, column=1, padx=(10, 0), sticky="ew")
            lbl(ri, "Question / Aim",
                font=F_SMALL, fg=C["muted"], bg=C["card"]).grid(
                row=1, column=1, padx=(10, 0), sticky="w")

            in_var = tk.StringVar()
            entry(ri, in_var, width=16).grid(
                row=0, column=2, padx=(8, 0), sticky="ew")
            lbl(ri, "Input (stdin)",
                font=F_SMALL, fg=C["muted"], bg=C["card"]).grid(
                row=1, column=2, padx=(8, 0), sticky="w")

            ri.columnconfigure(1, weight=1)
            self._rows.append({"no": no, "q": q_var, "inp": in_var})

        # Buttons
        bot = frm(self, bg=C["bg"])
        bot.pack(fill="x", padx=20, pady=10)
        btn(bot, "Cancel", self.destroy,
            bg=C["entry"], fg=C["muted"], px=12, py=6).pack(side="left")
        btn(bot, "Add All", self._confirm,
            bg=C["accent"], px=18, py=6).pack(side="right")

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
    """Add or edit one experiment.
    Shows a live preview of which code file will be matched as you type
    the experiment number."""

    def __init__(self, parent, title, on_save, data=None, prefill_no=""):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._on_save   = on_save
        self._code_dir  = getattr(parent, "_code_var", None)

        pad = frm(self, bg=C["bg"])
        pad.pack(padx=24, pady=18, fill="both")

        # ── Row 0: Experiment number ────────────────────────────────────────
        lbl(pad, "Experiment Number", font=F_BOLD).grid(
            row=0, column=0, sticky="w", pady=4)

        no_frm = frm(pad, bg=C["bg"])
        no_frm.grid(row=0, column=1, sticky="ew", padx=(10,0), pady=4)

        self._no = tk.StringVar(value=data["exp_no"] if data else prefill_no)
        eno = entry(no_frm, self._no, width=10)
        eno.pack(side="left")

        # Live file-match label
        self._match_lbl = lbl(no_frm, "  ←  type a number to see which file matches",
                               font=F_SMALL, fg=C["muted"], bg=C["bg"])
        self._match_lbl.pack(side="left", padx=(10, 0))

        self._no.trace_add("write", lambda *_: self._update_match())

        # ── Row 1: Question ─────────────────────────────────────────────────
        lbl(pad, "Question / Aim", font=F_BOLD).grid(
            row=1, column=0, sticky="nw", pady=4)
        self._q = textbox(pad, font=F_BODY, height=4, width=54)
        self._q.grid(row=1, column=1, sticky="ew", padx=(10,0), pady=4)
        if data:
            self._q.insert("1.0", data["question"])

        # ── Row 2-3: Input ──────────────────────────────────────────────────
        lbl(pad, "Input (stdin)", font=F_BOLD).grid(
            row=2, column=0, sticky="nw", pady=4)
        lbl(pad,
            "One value per\nline — fed to\nprogram as stdin\n\nLeave blank\nif not needed",
            font=F_SMALL, fg=C["muted"]).grid(row=3, column=0, sticky="nw")

        self._inp = textbox(pad, height=6, width=54)
        self._inp.grid(row=2, column=1, rowspan=2, sticky="ew",
                       padx=(10,0), pady=4)
        if data:
            self._inp.insert("1.0", data["input"])

        # ── Row 4: stdin preview ─────────────────────────────────────────────
        lbl(pad, "Stdin preview", font=F_SMALL, fg=C["muted"]).grid(
            row=4, column=0, sticky="nw", pady=(8,0))
        self._preview = tk.Text(
            pad, font=F_MONO_B, bg="#0D1117", fg="#3FB950",
            height=4, relief="flat", state="disabled",
            highlightbackground=C["border"], highlightthickness=1,
            width=54, padx=8, pady=4)
        self._preview.grid(row=4, column=1, sticky="ew",
                           padx=(10,0), pady=(8,0))
        self._inp.bind("<KeyRelease>", lambda e: self._update_preview())
        self._update_preview()

        lbl(pad, "💡 Each line above becomes one stdin entry for your program.",
            font=F_SMALL, fg=C["warn"]).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(6,0))

        # ── Buttons ──────────────────────────────────────────────────────────
        brow = frm(pad, bg=C["bg"])
        brow.grid(row=6, column=0, columnspan=2, pady=(14,0), sticky="e")
        btn(brow, "Cancel", self.destroy,
            bg=C["entry"], fg=C["muted"], px=12, py=6).pack(side="left", padx=4)
        btn(brow, "Save", self._save,
            bg=C["accent"], px=18, py=6).pack(side="left")

        pad.columnconfigure(1, weight=1)
        self._update_match()   # initial check

    def _update_match(self):
        """Show which file the typed exp number would match."""
        no = self._no.get().strip()
        if not no:
            self._match_lbl.configure(text="  ←  enter a number",
                                      fg=C["muted"])
            return

        code_dir = None
        if self._code_dir:
            code_dir = self._code_dir.get().strip()

        if not code_dir or not Path(code_dir).exists():
            self._match_lbl.configure(
                text=f"  (set Code Folder in Setup to see match)",
                fg=C["muted"])
            return

        from app.modules.code_mapper import CodeMapper
        hit = CodeMapper(Path(code_dir).resolve()).find(no)
        if hit:
            self._match_lbl.configure(
                text=f"  ✓  will match:  {hit.name}",
                fg=C["ok"])
        else:
            self._match_lbl.configure(
                text=f"  ✗  no file found for  '{no}'  in code folder",
                fg=C["err"])

    def _update_preview(self):
        raw   = self._inp.get("1.0", "end").rstrip("\n")
        lines = raw.splitlines() if raw.strip() else ["(no input)"]
        text  = "\n".join(f"  stdin[{i}] → {ln}"
                          for i, ln in enumerate(lines))
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
