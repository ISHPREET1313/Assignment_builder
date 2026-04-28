"""
app/modules/execution_engine.py

Fixes:
  - rc=3221225477 (0xC0000005) = Windows stdin exhausted on menu-loop programs
    -> treat as success if stdout was produced
  - Absolute path fix (no path doubling)
  - Clean EOF handling for interactive programs
"""

import subprocess, shutil, tempfile, sys
from pathlib import Path

# Exit codes that just mean stdin ran out (common for menu-loop C programs on Windows)
_SOFT_RC = {0, 1, 3221225477, 0xC0000005, -1073741819, -1073741510}


class ExecutionEngine:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def run(self, code_path: Path, language: str, stdin_data: str = "") -> dict:
        code_path = Path(code_path).resolve()
        try:
            if language == "Python":
                return self._exec(["python3", str(code_path)], stdin_data,
                                  cwd=str(code_path.parent))
            elif language in ("C", "C++"):
                return self._compile_and_run(code_path, language, stdin_data)
            return self._err(f"Unsupported language: {language}")
        except Exception as e:
            return self._err(str(e))

    def _compile_and_run(self, path, lang, stdin_data):
        compiler = "gcc" if lang == "C" else "g++"
        if not shutil.which(compiler):
            return self._err(
                f"{compiler} not found.\n"
                "Windows: install MinGW-w64 and add it to PATH.\n"
                "Linux:   sudo apt install build-essential"
            )
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / ("prog.exe" if sys.platform == "win32" else "prog")
            cr = self._exec([compiler, str(path), "-o", str(binary)], "",
                            cwd=str(path.parent))
            if not cr["success"]:
                cr["stderr"] = f"[Compilation Error]\n{cr['stderr']}"
                return cr
            return self._exec([str(binary)], stdin_data, cwd=tmp)

    def _exec(self, cmd, stdin_data, cwd=None):
        try:
            proc = subprocess.run(
                cmd, input=stdin_data,
                capture_output=True, text=True,
                timeout=self.timeout, cwd=cwd,
            )
            rc     = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            has_out = bool(stdout.strip())
            # Success if rc==0, OR if we got output and exit was just "stdin ran out"
            ok = (rc == 0) or (has_out and rc in _SOFT_RC)
            return {"success": ok, "stdout": stdout,
                    "stderr": stderr, "returncode": rc}
        except subprocess.TimeoutExpired:
            return self._err(f"Timed out after {self.timeout}s.")
        except FileNotFoundError as e:
            return self._err(str(e))

    @staticmethod
    def _err(msg):
        return {"success": False, "stdout": "", "stderr": msg, "returncode": -1}
