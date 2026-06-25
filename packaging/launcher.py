# packaging/launcher.py
"""
Single entry point for the desktop build.

Starts the FastAPI backend in a daemon thread, launches the Streamlit UI in the
main thread (Streamlit/Tornado must own the main thread), and opens the default
browser at the app. Works both unfrozen (for fast iteration) and frozen by
PyInstaller (the `.exe`).

    backend (uvicorn, 127.0.0.1:8000)  ── daemon thread
    frontend (streamlit, 127.0.0.1:8501) ── main thread
    browser ── opened once the UI port is up
"""

import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

BACKEND_PORT = 8000
UI_PORT = 8501


def _frozen() -> bool:
    return getattr(sys, "frozen", False)


def _redirect_output_if_windowed():
    """A windowed (console=False) PyInstaller build sets sys.stdout/stderr to
    None, so any write — our prints, uvicorn, Streamlit's logger — would raise.
    Redirect both to a log file beside the exe: output is hidden from the user
    but still recoverable for debugging."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        stream = open(
            Path(sys.executable).resolve().parent / "os-simulator.log",
            "w", buffering=1, encoding="utf-8",
        )
    except Exception:
        import io
        stream = io.StringIO()
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def _resolve_dirs():
    """Return (frontend_dir, backend_dir) for both frozen and source layouts."""
    if _frozen():
        # PyInstaller flattens bundled sources under _MEIPASS.
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base, base
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "frontend", repo_root / "backend"


FRONTEND_DIR, BACKEND_DIR = _resolve_dirs()

# Make backend modules (main, schemas, advisor, algorithms.*) and frontend
# modules (config, chatbot, llm) importable.
for _p in (str(BACKEND_DIR), str(FRONTEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Point the frontend's config.py at the in-process backend.
os.environ["API_BASE"] = f"http://127.0.0.1:{BACKEND_PORT}"


def _run_backend():
    import uvicorn
    import main  # backend/main.py -> exposes `app`

    uvicorn.run(main.app, host="127.0.0.1", port=BACKEND_PORT, log_level="warning")


def _wait_backend(timeout=20.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{BACKEND_PORT}/"
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _open_browser():
    # Give Streamlit a moment to bind the port before opening the tab.
    time.sleep(3.0)
    webbrowser.open(f"http://localhost:{UI_PORT}")


def _patch_streamlit_static_dir():
    """Frozen builds: Streamlit derives its static asset dir from `__file__`,
    which doesn't resolve to the PyInstaller _MEIPASS extraction — so the app
    index 404s. Point `get_static_dir` at the bundled copy when needed."""
    if not _frozen():
        return
    try:
        import streamlit.file_util as fu

        computed = fu.get_static_dir()
        bundled = os.path.join(sys._MEIPASS, "streamlit", "static")  # type: ignore[attr-defined]
        print(f"[launcher] streamlit static: computed={computed} exists={os.path.isdir(computed)}")
        if not os.path.isdir(computed) and os.path.isdir(bundled):
            fu.get_static_dir = lambda: bundled
            print(f"[launcher] patched static dir -> {bundled}")
    except Exception as exc:  # pragma: no cover
        print(f"[launcher] static-dir patch skipped: {exc}")


def _force_production_mode():
    """Pin Streamlit's developmentMode to False for frozen builds.

    Streamlit infers dev mode from whether it lives under site-packages; in a
    PyInstaller bundle it doesn't, so dev mode defaults ON — which skips the
    static index mount (the app 404s) and ignores server.port. A flag override
    can be wiped by a later config reparse, so pin it at the config *template*
    level (which every reparse deep-copies from) as well as the live options."""
    if not _frozen():
        return
    try:
        import streamlit.config as cfg

        cfg.get_config_options()  # ensure template + live options are built
        for store in (cfg._config_options_template, cfg._config_options):
            opt = (store or {}).get("global.developmentMode")
            if opt is not None:
                opt.set_value(False)
        print(f"[launcher] developmentMode pinned -> {cfg.get_option('global.developmentMode')}")
    except Exception as exc:  # pragma: no cover
        print(f"[launcher] could not pin production mode: {exc}")


def main_entry():
    _redirect_output_if_windowed()
    _force_production_mode()
    _patch_streamlit_static_dir()
    print("[launcher] starting backend ...")
    threading.Thread(target=_run_backend, daemon=True).start()
    if _wait_backend():
        print(f"[launcher] backend ready on :{BACKEND_PORT}")
    else:
        print("[launcher] WARNING: backend did not report ready; continuing anyway")

    threading.Thread(target=_open_browser, daemon=True).start()

    from streamlit.web import bootstrap

    app_path = str(FRONTEND_DIR / "app.py")
    flag_options = {
        # Streamlit infers "development mode" from whether it lives under
        # site-packages; in a PyInstaller bundle it doesn't, so dev mode defaults
        # ON — which skips the static index mount (app 404s) and ignores
        # server.port. Override it explicitly (env vars don't override this
        # computed/hidden option, but a flag option does).
        "global.developmentMode": False,
        "server.port": UI_PORT,
        "server.address": "127.0.0.1",
        "server.headless": True,
        "server.fileWatcherType": "none",
        "browser.gatherUsageStats": False,
        "logger.level": "error",
    }
    print(f"[launcher] starting UI on :{UI_PORT} ({app_path})")
    # bootstrap.run applies flag_options and fixes sys.path for the script dir.
    bootstrap.run(app_path, False, [], flag_options)


if __name__ == "__main__":
    main_entry()
