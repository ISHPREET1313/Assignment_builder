# AutoDocSystem 📄

**Automated Practical Documentation Generator** — runs your code, captures output, and builds a formatted Word document in one click.

Supports **Python · C · C++**. Uses your own previous experiment file as the style template so every report matches your college's format.

---

## ✨ Features

- **Template-based styling** — give it any `.docx` (your previous experiment) and the output will inherit its fonts, margins, headers, and page layout
- **Auto-executes code** — feeds stdin, captures stdout/stderr, renders output as an image
- **Multi-language** — Python, C (gcc), C++ (g++) in one pipeline
- **Separate inputs file** — keep test inputs in `inputs.txt` next to `questions.txt`
- **GUI** — clean desktop interface, no terminal needed after setup
- **Git-friendly** — clone, install, run

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/AutoDocSystem.git
cd AutoDocSystem
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Requires Python 3.10+**  
> For C/C++ support: `sudo apt install build-essential` (Linux) or install GCC via MinGW on Windows.

### 3. Run

```bash
python main.py
```

---

## 🖥️ Using the App

When the GUI opens:

| Field | What to select |
|---|---|
| **Template .docx** | Your previous experiment Word file — used to copy formatting |
| **Questions file** | `questions.txt` — contains experiment numbers, aims, and test inputs |
| **Code folder** | Folder with your `.py` / `.c` / `.cpp` files |
| **Output folder** | Where the final `.docx` report will be saved |

Click **🚀 Generate Report** — the log window shows live progress.

---

## 📁 Folder Structure

```
AutoDocSystem/
├── main.py                  ← Run this
├── requirements.txt
├── README.md
├── .gitignore
├── app/
│   ├── gui.py               ← GUI window
│   ├── pipeline.py          ← Orchestrates the pipeline
│   └── modules/
│       ├── question_parser.py
│       ├── code_mapper.py
│       ├── language_detector.py
│       ├── execution_engine.py
│       ├── output_handler.py
│       └── document_generator.py
└── sample/                  ← Try this first!
    ├── questions.txt
    ├── inputs.txt
    └── code_files/
        ├── exp1.py
        ├── exp2.py
        └── ...
```

---

## 📝 questions.txt Format

```
# One block per experiment, separated by a blank line
# Lines starting with # are comments

EXP: 1
QUESTION: Write a Python program to add two numbers.
INPUT: 3 5

EXP: 2
QUESTION: Write a C program to check even or odd.
INPUT: 7
```

| Field | Required | Description |
|---|---|---|
| `EXP` | ✅ | Experiment number — must match your filename (e.g. `exp1.py`) |
| `QUESTION` | ✅ | The aim / objective shown in the report |
| `INPUT` | optional | stdin passed to the program when running |

---

## 📥 inputs.txt (optional)

Place `inputs.txt` **in the same folder** as `questions.txt`. It overrides any `INPUT:` values in `questions.txt`.

```
EXP: 1
INPUT: 10 20

EXP: 2
INPUT: 13
```

---

## 📂 Code File Naming

The system auto-matches files by experiment number. All of these work:

```
exp1.py    exp_1.py    1.py    q1.c    prac1.cpp    experiment1.py
```

Supported extensions: `.py` `.c` `.cpp` `.cc` `.cxx`

---

## 🎨 Template Styling

The app opens your template `.docx` and inherits:
- Page size, margins, orientation
- All defined styles (Heading 1, Normal, etc.)
- Headers and footers (college name, logo, etc.)

Your experiment content is added using those styles, so the output looks identical to your manual documents.

---

## ⚙️ Requirements

| Requirement | Notes |
|---|---|
| Python 3.10+ | |
| `python-docx` | Word document generation |
| `Pillow` | Output image rendering |
| `gcc` / `g++` | Only needed for C/C++ experiments |
| `tkinter` | Bundled with Python (standard library) |

---

## 🐛 Troubleshooting

**"No code file found for Experiment N"**  
→ Make sure your file is named `expN.py` (or similar) in the selected code folder.

**Code runs but shows wrong output**  
→ Check the `INPUT:` field in `questions.txt` — it's fed as stdin to your program.

**C/C++ compilation error**  
→ Ensure `gcc`/`g++` is installed: `gcc --version`

**Template styles not applied**  
→ The template must be a valid `.docx` file. A blank Word document works too.

---

## 📜 License

MIT — free to use, share, and modify.


---

## 🖥️ Build a Standalone .exe (Windows)

So others don't need Python installed:

```bash
pip install pyinstaller
python build.py
```

Outputs `dist/AutoDocSystem.exe` — share that file and it just works.

---

## ✏️ No More .txt Files!

The new GUI has a built-in **Experiments editor** (📋 tab).
Click **+ Add** to enter your experiment number, question, and input directly.
Double-click any row to edit it. No `questions.txt` or `inputs.txt` needed.
