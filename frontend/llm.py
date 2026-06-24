# frontend/llm.py
"""
Local LLM runtime for the chatbot — Phi-3-mini-4k-instruct (Q4_K_M GGUF) via
llama-cpp-python, CPU-only.

Responsibilities (kept separate from the chat UI so a future backend `/parse`
endpoint can replace this layer without touching chatbot.py):

    resolve_model_path()  -> where is the .gguf?            (env / models/ / fallback)
    ensure_model()        -> download it if missing         (HF streaming, no extra deps)
    get_llm()             -> a cached, loaded Llama instance (loads once per session)
    chat(messages)        -> one chat completion
    runtime_status()      -> {llama_installed, model_present, model_path}

Per the PRD, the model is a PARSER/ROUTER, never the solver: chatbot.py uses it
to turn text into the existing input JSON; the FastAPI backend still computes the
real scheduling results.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests
import streamlit as st

# ── Paths & constants ──────────────────────────────────────────────────────
# frontend/llm.py  ->  project root is one level up from this file's dir.
_FRONTEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _FRONTEND_DIR.parent
MODELS_DIR = _PROJECT_ROOT / "models"

# Canonical local filename (matches the user's existing copy).
MODEL_FILENAME = "phi-3-mini-q4_k_m.gguf"

# Known fallback locations to reuse an already-downloaded copy (avoids a 2.4 GB
# duplicate on this dev machine). The user's model lives in the `nadi` project.
_FALLBACK_PATHS = [
    Path.home() / "code" / "nadi" / "ai_processing_core" / "models" / MODEL_FILENAME,
    Path.home() / "code" / "XXX" / "nadi-ai-processing-core" / "ai_processing_core" / "models" / MODEL_FILENAME,
]

# HuggingFace direct-download URL for Phi-3-mini-4k-instruct Q4_K_M (~2.4 GB).
DOWNLOAD_URL = (
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/"
    "resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
)

N_CTX = 4096


# ── Model resolution ───────────────────────────────────────────────────────
def resolve_model_path() -> str | None:
    """Return the path to a usable GGUF, or None if nothing is found.

    Search order:
      1. PHI3_MODEL_PATH env var (explicit override, e.g. set in .env)
      2. any *.gguf inside the project-root models/ directory
      3. known fallback copies (the user's `nadi` project)
    """
    env_path = os.getenv("PHI3_MODEL_PATH")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path))

    if MODELS_DIR.is_dir():
        # Prefer the canonical filename, else the first .gguf present.
        canonical = MODELS_DIR / MODEL_FILENAME
        if canonical.is_file():
            return str(canonical)
        for gguf in sorted(MODELS_DIR.glob("*.gguf")):
            return str(gguf)

    for path in _FALLBACK_PATHS:
        if path.is_file():
            return str(path)

    return None


def llama_installed() -> bool:
    """True if the llama-cpp-python runtime can be imported."""
    try:
        import llama_cpp  # noqa: F401
        return True
    except Exception:
        return False


def runtime_status() -> dict:
    """Snapshot for the UI to decide between LLM mode and offline fallback."""
    path = resolve_model_path()
    return {
        "llama_installed": llama_installed(),
        "model_present": path is not None,
        "model_path": path,
    }


# ── Download ───────────────────────────────────────────────────────────────
def ensure_model(progress_cb=None) -> str:
    """Ensure a GGUF exists locally; download into models/ if missing.

    `progress_cb(fraction, downloaded_bytes, total_bytes)` is called during the
    stream so the UI can render a progress bar. Returns the model path.
    """
    existing = resolve_model_path()
    if existing:
        return existing

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / MODEL_FILENAME
    tmp = dest.with_suffix(dest.suffix + ".part")

    with requests.get(DOWNLOAD_URL, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(downloaded / total, downloaded, total)

    tmp.replace(dest)  # atomic: only become the real file once fully written
    return str(dest)


# ── Inference ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading Phi-3 model (first time only)…")
def get_llm(model_path: str):
    """Load the GGUF once and cache it for the whole Streamlit session.

    Cached on `model_path` so switching models re-loads, but normal reruns reuse
    the already-loaded instance.
    """
    from llama_cpp import Llama

    return Llama(
        model_path=model_path,
        n_ctx=N_CTX,
        n_threads=os.cpu_count() or 4,
        verbose=False,
        # CPU-only for now (runs on any machine). GPU offload (n_gpu_layers) can
        # be added later once a CUDA build of llama-cpp-python is in use.
    )


def chat_json(messages, temperature: float = 0.1, max_tokens: int = 512) -> dict:
    """Run one chat completion constrained to a JSON object and return it parsed.

    Uses llama.cpp's grammar-constrained `response_format={"type":"json_object"}`
    so small models reliably emit valid JSON (the model is a parser, not a
    solver — it only produces the input contract; the backend computes results).

    Raises RuntimeError if the runtime/model isn't available, or ValueError if
    the output can't be parsed — either way the caller falls back to the offline
    rule-based parser.
    """
    path = resolve_model_path()
    if not path:
        raise RuntimeError("No Phi-3 model found.")
    if not llama_installed():
        raise RuntimeError("llama-cpp-python is not installed.")

    llm = get_llm(path)
    out = llm.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    content = out["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)  # safety net
        if m:
            return json.loads(m.group(0))
        raise ValueError(f"Model did not return JSON: {content[:200]!r}")
