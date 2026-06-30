# os_sim.spec — PyInstaller recipe for the OS Simulator desktop build.
#
# Build (from the packaging/ dir, using the frontend env which has both the
# frontend and backend runtime deps plus pyinstaller):
#     uv run --project ../frontend pyinstaller os_sim.spec
#
# Produces dist/OS-Simulator.exe (onefile). The launcher starts the FastAPI
# backend in-thread and the Streamlit UI, then opens the browser.

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

SPEC_DIR = Path(SPECPATH)            # packaging/
REPO = SPEC_DIR.parent
FRONTEND = REPO / "frontend"
BACKEND = REPO / "backend"

# Make backend + frontend modules importable to collect_submodules below.
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(FRONTEND))

datas, binaries, hiddenimports = [], [], []

# Pull everything (data files, native libs, submodules) for the heavy packages
# that are only reached through the runtime-loaded Streamlit scripts, so static
# analysis of launcher.py alone wouldn't find them.
for pkg in (
    "streamlit", "plotly", "altair", "narwhals",
    "pandas", "numpy", "pyarrow", "networkx", "llama_cpp",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # pragma: no cover - build-time only
        print(f"[spec] skipping {pkg}: {exc}")

# Streamlit (and friends) read their own versions via importlib.metadata.
for meta in ("streamlit", "plotly", "altair", "pandas", "numpy", "pyarrow"):
    try:
        datas += copy_metadata(meta)
    except Exception as exc:  # pragma: no cover
        print(f"[spec] no metadata for {meta}: {exc}")

# The frontend UI scripts are loaded by Streamlit at runtime (not imported by
# launcher.py), so ship them as data at the bundle root; Streamlit's bootstrap
# adds that dir to sys.path so their sibling imports resolve.
for f in ("app.py", "config.py", "chatbot.py", "llm.py"):
    datas.append((str(FRONTEND / f), "."))

# The `components` package (gantt charts, etc.) is imported lazily inside app.py
# at runtime (e.g. `from components.gantt import render_gantt`), so analysing
# launcher.py alone never sees it. Ship the whole package, preserving its folder
# so it imports as `components.*` from the bundle root.
for comp in sorted((FRONTEND / "components").glob("*.py")):
    datas.append((str(comp), "components"))

# Backend: launcher.py imports `main`, which statically imports the algorithm
# modules; collect them explicitly to be safe.
hiddenimports += collect_submodules("algorithms")
hiddenimports += [
    "main", "schemas", "advisor",
    "uvicorn", "fastapi", "pydantic", "requests",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(BACKEND), str(FRONTEND)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="OS-Simulator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,         # windowless: no terminal window (logs go to os-simulator.log)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
