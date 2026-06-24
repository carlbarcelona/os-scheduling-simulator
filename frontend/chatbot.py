# frontend/chatbot.py
"""
Conversational ("chatbot") input module for the OS Scheduling Simulator.

WHAT IT IS
    A drop-in Streamlit page. Instead of filling sidebar fields, the user
    describes a CPU workload in plain English in one chat box, e.g.

        "P1 arrives 0 runs 5, P2 at 2 needs 3, use round robin q=2 and run it"
        "I have arrival times 0, 2, 4 and bursts 5, 3, 8"

    A local Phi-3-mini GGUF model (via llama-cpp-python) reads the message,
    replies conversationally, and emits a structured action that builds the
    process list and — on request — runs the REAL simulation through the
    existing FastAPI backend.

ARCHITECTURE (PRD Phase 3 — the model is a parser/router, NOT a solver)
    user text ─▶ Phi-3 (llm.py) ─▶ {action, processes, algorithm, quantum}
              ─▶ written into the SHARED st.session_state.processes
              ─▶ on "run": existing backend endpoint computes the real result
    The model never produces scheduling numbers; the backend stays the source
    of truth. If the model is unavailable, a built-in rule-based parser keeps
    the feature working offline (graceful degradation).

INTEGRATION (for the frontend engineer) — ~2 lines in app.py
    page = st.sidebar.radio("Navigate",
        [..., "Compare", "Recommend", "Chatbot"], ...)
    ...
    elif page == "Chatbot":
        from chatbot import render_chatbot
        render_chatbot()

    The module owns its own `chat_*` state, writes parsed processes into the
    shared `st.session_state.processes` (same shape as app.py:180-187), and
    mirrors the chosen algorithm into `sticky_cpu_algorithm` / `last_algorithm`,
    so the Scheduler and Compare pages immediately reflect chat input.

    Standalone preview:  `streamlit run chatbot.py`
"""

import json
import re

import requests
import streamlit as st

from config import (
    FCFS_API,
    SJF_NP_API,
    SJF_PRE_API,
    ROUND_ROBIN_API,
    PRIORITY_NP_API,
    PRIORITY_PRE_API,
)
import llm

# Display-name -> endpoint. Mirrors ALGORITHM_MAP in app.py (config.py contract).
CPU_ALGO_API = {
    "FCFS": FCFS_API,
    "SJF Non-Preemptive": SJF_NP_API,
    "SJF Preemptive": SJF_PRE_API,
    "Round Robin": ROUND_ROBIN_API,
    "Priority Non-Preemptive": PRIORITY_NP_API,
    "Priority Preemptive": PRIORITY_PRE_API,
}
VALID_ALGOS = set(CPU_ALGO_API)

WELCOME = (
    "Hi! I'm your scheduling assistant. Describe your CPU workload in plain "
    "English and I'll build the process list for you — no forms needed.\n\n"
    "Try:\n"
    "- `P1 arrival 0 burst 5, P2 arrival 2 burst 3, P3 arrival 4 burst 8`\n"
    "- `use round robin with quantum 2 and run it`\n"
    "- `remove P2` · `clear` · `show` · `help`"
)

SYSTEM_PROMPT = """You are the INPUT PARSER for an OS CPU-scheduling simulator.
You DO NOT calculate scheduling results, schedules, or metrics — a separate
backend does that. Your only job is to turn the user's message into one JSON
action object.

Reply with a SINGLE JSON object and nothing else (no prose, no code fences),
with EXACTLY these keys:
{
  "message": "<one short friendly sentence to the user>",
  "action": "add" | "clear" | "remove" | "run" | "none",
  "processes": [{"pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 0}],
  "algorithm": "FCFS" | "SJF Non-Preemptive" | "SJF Preemptive" | "Round Robin" | "Priority Non-Preemptive" | "Priority Preemptive" | null,
  "quantum": null,
  "remove_pid": null
}

Rules:
- Only include processes the user EXPLICITLY described. NEVER invent numbers.
- Omit "priority" unless the user gave one.
- "run"/"simulate"/"solve" => action "run".
- Just adding processes => "add". Clearing the list => "clear" (processes []).
- Removing one => "remove" with "remove_pid" (e.g. "P2").
- Set "algorithm"/"quantum" whenever the user mentions them, with any action.
- If required info is missing (e.g. Round Robin needs a quantum), use action
  "none" and ask for it in "message".
- "message" must NOT contain any computed schedule, ordering, or metrics.

CRITICAL:
- "processes" must contain ONLY processes described in the user's LATEST message;
  use [] if none. NEVER reuse processes from earlier example messages.
- Set "action":"run" ONLY if the user explicitly asks to run/simulate/solve.
  Otherwise use "add" (when processes are given) or "none".
- "algorithm" must be null unless the user NAMES one, and must be EXACTLY one of
  the listed strings (never an abbreviation like "SJF")."""

# A few diverse examples to pin the format AND teach the model not to over-act.
def _ex(user, obj):
    return [
        {"role": "user", "content": user},
        {"role": "assistant", "content": json.dumps(obj)},
    ]


_FEWSHOT = (
    _ex(
        "add P1 arrival 0 burst 4 and P2 arrival 1 burst 3",
        {
            "message": "Added P1 and P2.",
            "action": "add",
            "processes": [
                {"pid": "P1", "arrival_time": 0, "burst_time": 4},
                {"pid": "P2", "arrival_time": 1, "burst_time": 3},
            ],
            "algorithm": None,
            "quantum": None,
            "remove_pid": None,
        },
    )
    + _ex(
        "use round robin with quantum 3 and run it",
        {
            "message": "Running Round Robin with quantum 3.",
            "action": "run",
            "processes": [],
            "algorithm": "Round Robin",
            "quantum": 3,
            "remove_pid": None,
        },
    )
    + _ex(
        "remove P3",
        {
            "message": "Removed P3.",
            "action": "remove",
            "processes": [],
            "algorithm": None,
            "quantum": None,
            "remove_pid": "P3",
        },
    )
)


# ──────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────────────────
def _init_state():
    """Initialise this module's keys plus the shared keys it relies on.

    `setdefault` keeps the module safe both standalone and mounted in app.py
    (which already creates `processes`, `sticky_cpu_algorithm`, etc.).
    """
    st.session_state.setdefault("processes", [])               # SHARED with app.py
    st.session_state.setdefault("sticky_cpu_algorithm", "FCFS")  # SHARED
    st.session_state.setdefault("last_algorithm", None)        # SHARED
    st.session_state.setdefault("chat_quantum", 2)
    st.session_state.setdefault(
        "chat_history", [{"role": "assistant", "content": WELCOME, "llm": WELCOME}]
    )


# ──────────────────────────────────────────────────────────────────────────
# SHARED RENDER / SIM HELPERS  (used by both the LLM and fallback paths)
# ──────────────────────────────────────────────────────────────────────────
def _processes_md(processes):
    if not processes:
        return "_No processes yet._"
    has_pr = any("priority" in p for p in processes)
    header = "| PID | Arrival | Burst" + (" | Priority" if has_pr else "") + " |"
    sep = "|---|---|---" + ("|---" if has_pr else "") + "|"
    rows = [header, sep]
    for p in processes:
        row = f"| {p['pid']} | {p['arrival_time']} | {p['burst_time']}"
        if has_pr:
            row += f" | {p.get('priority', '—')}"
        rows.append(row + " |")
    return "\n".join(rows)


def _result_md(algorithm, result):
    lines = [
        f"**Ran {algorithm}** ✅",
        f"- Avg Waiting Time: **{result.get('avg_waiting_time', 0):.2f}**",
        f"- Avg Turnaround Time: **{result.get('avg_turnaround_time', 0):.2f}**",
        f"- CPU Utilization: **{result.get('cpu_utilization', 0):.2f}%**",
    ]
    order = " → ".join(b["pid"] for b in result.get("schedule", []))
    if order:
        lines.append(f"- Execution order: {order}")
    lines.append("\n_Open the **Scheduler** or **Compare** page for the full Gantt chart._")
    return "\n".join(lines)


def _run_simulation(algorithm, processes, quantum):
    payload = {"processes": processes}
    if algorithm == "Round Robin" and quantum:
        payload["quantum"] = quantum
    resp = requests.post(CPU_ALGO_API[algorithm], json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _run_and_report(parts):
    """Run the current workload via the backend; append result/errors to `parts`."""
    algo = st.session_state.sticky_cpu_algorithm
    if not st.session_state.processes:
        parts.append("There are no processes to run yet — describe some first.")
        return
    if algo == "Round Robin" and not st.session_state.get("chat_quantum"):
        parts.append("Round Robin needs a quantum. Say e.g. `quantum 2`.")
        return
    try:
        result = _run_simulation(
            algo, st.session_state.processes, st.session_state.get("chat_quantum")
        )
        st.session_state.last_algorithm = algo
        parts.append(_result_md(algo, result))
    except requests.exceptions.ConnectionError:
        parts.append("⚠️ Couldn't reach the backend. Is the API running?")
    except requests.exceptions.Timeout:
        parts.append("⚠️ The backend timed out. Try again.")
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        parts.append(f"⚠️ Backend error: {detail}")


def _merge_processes(new_procs):
    """Add/replace processes in the shared list, preserving order."""
    by_pid = {p["pid"]: p for p in st.session_state.processes}
    for p in new_procs:
        by_pid[p["pid"]] = p
    existing_order = [p["pid"] for p in st.session_state.processes]
    new_only = [p["pid"] for p in new_procs if p["pid"] not in existing_order]
    st.session_state.processes = [by_pid[pid] for pid in existing_order + new_only]


def _sanitize_process(raw, fallback_pid=None):
    """Coerce a model-produced process dict into the backend's contract.

    `fallback_pid` recovers entries where the model omitted/mangled the pid but
    still gave a valid burst — better than silently dropping the process.
    """
    if not isinstance(raw, dict):
        return None
    try:
        pid = str(raw.get("pid") or fallback_pid or "").strip()
        p = {
            "pid": pid,
            "arrival_time": int(raw.get("arrival_time", 0)),
            "burst_time": int(raw["burst_time"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
    if p["burst_time"] <= 0 or not p["pid"]:
        return None
    if raw.get("priority") is not None:
        try:
            p["priority"] = int(raw["priority"])
        except (TypeError, ValueError):
            pass
    return p


# ──────────────────────────────────────────────────────────────────────────
# ACTION APPLICATION  (shared by LLM JSON output and could back a backend /parse)
# ──────────────────────────────────────────────────────────────────────────
def _normalize_algo(value):
    """Map a model-produced algorithm string to a canonical name, or None.

    Accepts exact names and common shorthands ("SJF", "RR", "priority") by
    reusing the fallback detector.
    """
    if not value:
        return None
    if value in VALID_ALGOS:
        return value
    return detect_algorithm(str(value))


def apply_action(action: dict):
    """Apply a structured action dict; return extra markdown for the reply."""
    parts = []

    algorithm = _normalize_algo(action.get("algorithm"))
    if algorithm in VALID_ALGOS:
        st.session_state.sticky_cpu_algorithm = algorithm
        st.session_state.last_algorithm = algorithm
        parts.append(f"Algorithm set to **{algorithm}**.")

    quantum = action.get("quantum")
    if isinstance(quantum, int) and quantum > 0:
        st.session_state.chat_quantum = quantum
        parts.append(f"Quantum set to **{quantum}**.")

    kind = action.get("action", "none")

    if kind == "clear":
        st.session_state.processes = []
        parts.append("Cleared the process list. 🧹")

    elif kind == "remove":
        pid = str(action.get("remove_pid") or "").strip()
        before = len(st.session_state.processes)
        st.session_state.processes = [p for p in st.session_state.processes if p["pid"] != pid]
        if len(st.session_state.processes) < before:
            parts.append(f"Removed **{pid}**.\n\n{_processes_md(st.session_state.processes)}")
        else:
            parts.append(f"Couldn't find **{pid}**.\n\n{_processes_md(st.session_state.processes)}")

    elif kind in ("add", "run"):
        raw_list = action.get("processes") or []
        clean = [
            p
            for p in (
                _sanitize_process(r, fallback_pid=f"P{i + 1}")
                for i, r in enumerate(raw_list)
            )
            if p
        ]
        if clean:
            _merge_processes(clean)
            parts.append(
                f"Added/updated **{len(clean)}** process(es):\n\n"
                + _processes_md(st.session_state.processes)
            )
        if kind == "run":
            _run_and_report(parts)

    return "\n\n".join(parts)


# ──────────────────────────────────────────────────────────────────────────
# LLM PATH
# ──────────────────────────────────────────────────────────────────────────
def _llm_messages(user_text):
    """Build the message list for the model from recent history + current state."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += _FEWSHOT
    # Last few turns for context (use the clean 'llm' content, not rich markdown).
    for msg in st.session_state.chat_history[-6:]:
        content = msg.get("llm") or msg.get("content", "")
        if content:
            messages.append({"role": msg["role"], "content": content})
    state = (
        f"[state] current processes: {json.dumps(st.session_state.processes)}; "
        f"algorithm: {st.session_state.sticky_cpu_algorithm}; "
        f"quantum: {st.session_state.chat_quantum}"
    )
    messages.append({"role": "system", "content": state})
    messages.append({"role": "user", "content": user_text})
    return messages


def _llm_turn(user_text):
    """Run one LLM turn. Returns (display_md, assistant_natural_text).

    Raises on model/parse failure so parse_message() can fall back to the
    offline rule-based parser.
    """
    action = llm.chat_json(_llm_messages(user_text))  # grammar-constrained JSON
    natural = str(action.get("message") or "").strip()
    extra = apply_action(action)
    display = "\n\n".join(p for p in [natural, extra] if p) or "Done."
    return display, natural or "Done."


# ──────────────────────────────────────────────────────────────────────────
# OFFLINE FALLBACK PATH  (rule-based — works with no model installed)
# ──────────────────────────────────────────────────────────────────────────
def _grab_number_list(text, keyword_re):
    m = re.search(
        keyword_re + r"\s*(?:of|:|=|are|is)?\s*((?:\d+\s*(?:,|and|\s)\s*)*\d+)",
        text,
        re.I,
    )
    if not m:
        return None
    nums = re.findall(r"\d+", m.group(1))
    return [int(n) for n in nums] if nums else None


def _num_after(window, keyword_re):
    m = re.search(r"(?:" + keyword_re + r")\D*?(\d+)", window, re.I)
    return int(m.group(1)) if m else None


def extract_processes(text):
    """Rule-based process extraction. Returns (processes, skipped_pids)."""
    arrivals = _grab_number_list(text, r"arrival(?:\s*times?)?")
    bursts = _grab_number_list(text, r"burst(?:\s*times?)?")
    if (
        arrivals and bursts
        and len(arrivals) == len(bursts)
        and (len(arrivals) > 1 or len(bursts) > 1)
    ):
        priorities = _grab_number_list(text, r"priorit(?:y|ies)")
        procs = []
        for i in range(len(arrivals)):
            p = {"pid": f"P{i + 1}", "arrival_time": arrivals[i], "burst_time": bursts[i]}
            if priorities and len(priorities) == len(arrivals):
                p["priority"] = priorities[i]
            procs.append(p)
        return procs, []

    procs, skipped = [], []
    matches = list(re.finditer(r"(?:process\s*)?\bp\s*0*(\d+)\b", text, re.I))
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        window = text[start:end]
        arrival = _num_after(window, r"arrival|arrives?|arriving|arr\b")
        burst = _num_after(window, r"burst|bt\b|duration|cpu|needs?|runs?")
        priority = _num_after(window, r"priorit|prio\b|\bpr\b")
        if arrival is None and burst is None:
            nums = re.findall(r"\d+", window)
            if len(nums) >= 2:
                arrival, burst = int(nums[0]), int(nums[1])
                if len(nums) >= 3:
                    priority = int(nums[2])
        pid = f"P{m.group(1)}"
        if burst is None:
            skipped.append(pid)
            continue
        p = {"pid": pid, "arrival_time": arrival or 0, "burst_time": burst}
        if priority is not None:
            p["priority"] = priority
        procs.append(p)
    return procs, skipped


def detect_algorithm(text):
    t = text.lower()
    if "round robin" in t or re.search(r"\brr\b", t):
        return "Round Robin"
    if "sjf" in t or "shortest job" in t:
        return "SJF Preemptive" if ("pre" in t and "non" not in t) else "SJF Non-Preemptive"
    if "priority" in t:
        return "Priority Preemptive" if ("pre" in t and "non" not in t) else "Priority Non-Preemptive"
    if "fcfs" in t or "first come" in t or "first-come" in t:
        return "FCFS"
    return None


def detect_quantum(text):
    m = re.search(r"(?:quantum|time\s*slice|\bq\b)\s*(?:=|:|of)?\s*(\d+)", text, re.I)
    return int(m.group(1)) if m else None


def _wants_run(text):
    return bool(re.search(r"\b(run|simulate|solve|compute|execute)\b", text, re.I))


def _fallback_turn(user_text):
    """Rule-based router. Returns (display_md, natural_text)."""
    t = user_text.strip()
    low = t.lower()

    if re.search(r"\b(help|how do|usage|example|what can you)\b", low):
        return WELCOME, WELCOME

    if re.search(r"\b(clear|reset|start over|empty)\b", low) or re.search(
        r"\b(remove|delete)\s+all\b", low
    ):
        st.session_state.processes = []
        msg = "Cleared the process list. 🧹"
        return msg, msg

    rm = re.search(r"\b(?:remove|delete|drop)\b\D*\bp\s*0*(\d+)\b", low)
    if rm:
        pid = f"P{rm.group(1)}"
        before = len(st.session_state.processes)
        st.session_state.processes = [p for p in st.session_state.processes if p["pid"] != pid]
        found = len(st.session_state.processes) < before
        msg = (f"Removed **{pid}**." if found else f"Couldn't find **{pid}**.")
        return f"{msg}\n\n{_processes_md(st.session_state.processes)}", msg

    if re.search(r"\b(show|list|display|current)\b", low) and not re.search(r"\d", low):
        return f"Current processes:\n\n{_processes_md(st.session_state.processes)}", "Here's the list."

    parts = []
    algorithm = detect_algorithm(t)
    quantum = detect_quantum(t)
    procs, skipped = extract_processes(t)

    if algorithm:
        st.session_state.sticky_cpu_algorithm = algorithm
        st.session_state.last_algorithm = algorithm
        parts.append(f"Algorithm set to **{algorithm}**.")
    if quantum is not None:
        st.session_state.chat_quantum = quantum
        parts.append(f"Quantum set to **{quantum}**.")
    if procs:
        _merge_processes(procs)
        parts.append(
            f"Added/updated **{len(procs)}** process(es):\n\n"
            + _processes_md(st.session_state.processes)
        )
    if skipped:
        parts.append(
            "⚠️ I saw **" + ", ".join(skipped) + "** but couldn't find a burst time — "
            "tell me e.g. `P2 burst 4`."
        )
    if _wants_run(t):
        _run_and_report(parts)

    if not parts:
        msg = (
            "I couldn't pull any processes out of that. Try "
            "`P1 arrival 0 burst 5, P2 arrival 2 burst 3` — or type `help`."
        )
        return msg, msg
    display = "\n\n".join(parts)
    return display, display


# ──────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────
def parse_message(user_text, use_llm: bool):
    """Turn a chat message into (display_md, assistant_natural_text).

    Uses the Phi-3 model when available; otherwise the offline rule-based parser.
    A future backend `/parse` endpoint can slot in here unchanged.
    """
    if use_llm:
        try:
            return _llm_turn(user_text)
        except Exception as e:
            display, natural = _fallback_turn(user_text)
            note = f"_(model unavailable: {e} — used the offline parser)_"
            return f"{display}\n\n{note}", natural
    return _fallback_turn(user_text)


# ──────────────────────────────────────────────────────────────────────────
# MODEL SETUP PANEL
# ──────────────────────────────────────────────────────────────────────────
def _render_model_panel():
    """Show model status; offer download if missing. Returns True if LLM is usable."""
    status = llm.runtime_status()

    if not status["llama_installed"]:
        st.warning(
            "**Offline mode** — `llama-cpp-python` isn't installed, so I'm using the "
            "built-in rule-based parser. To enable the full Phi-3 bot, install the CPU "
            "wheel:\n\n"
            "```\npip install llama-cpp-python --extra-index-url "
            "https://abetlen.github.io/llama-cpp-python/whl/cpu\n```"
        )
        return False

    if not status["model_present"]:
        st.info("Phi-3 model not found. Download it once (~2.4 GB) to enable the full bot.")
        if st.button("⬇️ Download Phi-3 model"):
            bar = st.progress(0.0, text="Starting download…")

            def _cb(frac, done, total):
                bar.progress(min(frac, 1.0), text=f"Downloading… {done/1e9:.2f} / {total/1e9:.2f} GB")

            try:
                llm.ensure_model(progress_cb=_cb)
                bar.progress(1.0, text="Done!")
                st.success("Model downloaded. Reloading…")
                st.rerun()
            except Exception as e:
                st.error(f"Download failed: {e}")
        st.caption("Until then I'll use the offline rule-based parser.")
        return False

    st.success(f"Phi-3 ready · `{status['model_path']}`")
    return True


# ──────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────
def render_chatbot():
    """Render the chat page. The only symbol app.py needs to import."""
    _init_state()

    st.title("💬 Chat Input")
    st.caption(
        "Describe your CPU workload in plain English instead of using the sidebar forms. "
        "Anything entered here is shared with the Scheduler and Compare pages."
    )

    use_llm = _render_model_panel()

    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.markdown(
            f"**Algorithm:** `{st.session_state.sticky_cpu_algorithm}`  ·  "
            f"**Quantum:** `{st.session_state.chat_quantum}`  ·  "
            f"**Processes:** `{len(st.session_state.processes)}`"
        )
    with top_r:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.chat_history = [{"role": "assistant", "content": WELCOME, "llm": WELCOME}]
            st.rerun()

    st.divider()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("e.g. 'P1 arrival 0 burst 5, P2 arrival 2 burst 3, run FCFS'")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt, "llm": prompt})
        with st.spinner("Thinking…"):
            display, natural = parse_message(prompt, use_llm)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": display, "llm": natural}
        )
        st.rerun()


# Allow standalone preview:  `streamlit run chatbot.py`
if __name__ == "__main__":
    st.set_page_config(page_title="Chat Input", page_icon="💬", layout="wide")
    render_chatbot()
