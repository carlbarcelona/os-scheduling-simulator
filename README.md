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