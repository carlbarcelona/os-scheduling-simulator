# OS Scheduling Simulator

An interactive web app for simulating and visualizing OS CPU scheduling algorithms — FCFS, SJF, Round Robin, Priority, and MLFQ — with deadlock detection and a scheduling recommendation engine.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/install.sh) — install via terminal:
  ```bash
  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

  # Mac / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) *(only if running via Docker)*

## Running

Clone the repo first:

```bash
git clone https://github.com/carlbarcelona/os-scheduling-simulator.git
```

### With uv (recommended for development)

```bash
# backend
cd backend && uv sync 
uv run uvicorn main:app --reload

# frontend
cd frontend && uv sync
uv run streamlit run app.py
```

### With Docker

```bash
docker compose up --build
```

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:8501      |
| API docs | http://localhost:8000/docs |

## Desktop build (.exe)

A single double-click executable that starts the backend + UI internally and opens
your browser at the app. Built with PyInstaller; the build env is the `frontend`
project (it carries both the frontend and backend runtime deps plus PyInstaller).

```bash
cd packaging
uv run --project ../frontend pyinstaller os_sim.spec
# -> dist/OS-Simulator.exe
```

Run it by double-clicking `dist/OS-Simulator.exe` (a console window shows startup
logs, then a browser tab opens).

**AI chatbot model:** the ~2.4 GB Phi-3 GGUF model is **not** bundled. On first use of
the Chatbot, the app detects whether the model is present and, if not, offers to
download it into a `models/` folder **next to the executable**. Once downloaded it's
reused on the next launch. Without the model (or if the native LLM runtime can't
load), the chatbot falls back to an offline rule-based parser and the simulator
works fully offline regardless.