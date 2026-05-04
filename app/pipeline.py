"""
app/pipeline.py  —  Orchestrates the full doc-generation pipeline.
"""

import datetime, queue
from pathlib import Path

from app.modules.code_mapper        import CodeMapper
from app.modules.language_detector  import LanguageDetector
from app.modules.execution_engine   import ExecutionEngine
from app.modules.output_handler     import OutputHandler
from app.modules.document_generator import DocumentGenerator


class Pipeline:
    def __init__(self, cfg: dict, q: queue.Queue):
        self.template    = Path(cfg["template"])
        self.experiments = cfg["experiments"]
        self.code_dir    = Path(cfg["code_dir"]).resolve()
        self.out_dir     = Path(cfg["out_dir"])
        self.q           = q
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _log(self, msg, level="DIM"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.q.put(("LOG", (level, f"[{ts}]  {msg}")))

    def info(self, m):  self._log(m, "INFO")
    def warn(self, m):  self._log(m, "WARN")
    def error(self, m): self._log(m, "ERROR")
    def ok(self, m):    self._log(m, "SUCCESS")
    def dim(self, m):   self._log(m, "DIM")

    def run(self):
        self.info("═══  AutoDocSystem  ═══")
        self.info(f"Template : {self.template.name}")
        self.info(f"Code dir : {self.code_dir}")

        if not self.experiments:
            self.warn("No experiments — add some in the Experiments tab.")
            return

        mapper   = CodeMapper(self.code_dir)
        detector = LanguageDetector()
        engine   = ExecutionEngine(timeout=15)
        handler  = OutputHandler(self.out_dir / "img_tmp")
        docgen   = DocumentGenerator(self.template, self.out_dir)

        # ── Scan & show all files in code folder ───────────────────────────
        all_files = mapper.all_files()
        if not all_files:
            self.error(f"No supported source files found in:\n  {self.code_dir}")
            self.error("Supported: .py  .c  .cpp  .cc  .cxx")
            self.warn("Check that the correct folder is selected in Setup.")
            return

        self.info(f"Files found in code folder ({len(all_files)}):")
        for f in all_files:
            self.dim(f"    {f.name}")

        # ── Process each experiment ────────────────────────────────────────
        results = []
        total   = len(self.experiments)

        for idx, entry in enumerate(self.experiments, 1):
            exp_no   = entry["exp_no"]
            question = entry["question"]
            stdin_in = entry.get("input", "")

            self.q.put(("PROGRESS", (idx - 1, total)))
            self.info(f"─── Experiment {exp_no} ───────────────────────")

            code_path = mapper.find(exp_no)

            if code_path is None:
                self.error(f"  No file matched for Experiment '{exp_no}'")
                self.warn( f"  Expected a file like: exp{exp_no}.py / Q{exp_no}.c / {exp_no}.cpp")
                self.warn( f"  Files in folder: {[f.name for f in all_files]}")
                continue

            self.dim(f"  Matched  : {code_path.name}")
            language    = detector.detect(code_path)
            source_code = code_path.read_text(encoding="utf-8", errors="replace")
            self.dim(f"  Language : {language}")

            result  = engine.run(code_path, language, stdin_in)
            ok_run  = result["success"]
            out_txt = result["stdout"].strip()
            err_txt = result["stderr"].strip()

            if ok_run:
                output_text = out_txt or "(no output)"
                if err_txt:
                    output_text += f"\n[stderr]\n{err_txt}"
                self.ok(f"  ✓ rc={result['returncode']}  {len(out_txt)} chars output")
            else:
                output_text = f"[ERROR  rc={result['returncode']}]\n{err_txt}"
                self.error(f"  ✗ rc={result['returncode']} — {err_txt[:120]}")

            img_path = handler.to_image(output_text, exp_no)
            self.dim(f"  Image    : {img_path.name}")

            results.append({
                "exp_no"     : exp_no,
                "exp_label"  : entry.get("exp_label", "").strip() or exp_no,
                "question"   : question,
                "language"   : language,
                "source_code": source_code,
                "output_text": output_text,
                "img_path"   : img_path,
            })

        self.q.put(("PROGRESS", (total, total)))

        if not results:
            self.warn("Nothing to document — no experiments were processed.")
            return

        self.info(f"Building Word document ({len(results)} experiment(s))…")
        doc_path = docgen.generate(results)
        self.ok(f"Saved → {doc_path.name}")
        self.q.put(("STATUS", f"✅  {doc_path.name}"))
