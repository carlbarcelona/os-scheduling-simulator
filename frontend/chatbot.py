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

import html
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

# Grammar-friendly JSON schema for the model's action object. Constrains output to
# objects/arrays/enums/primitives only (no null-unions, no regex patterns) so
# llama.cpp's `from_json_schema` can build a grammar from it — bounding the model
# to exactly this shape and preventing the truncated/invalid JSON that crashed
# parsing. Only `message` + `action` are required; everything else is optional and
# simply omitted when unused.
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "action": {
            "type": "string",
            "enum": ["add", "clear", "remove", "run", "explain", "none"],
        },
        "processes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pid": {"type": "string"},
                    "arrival_time": {"type": "integer"},
                    "burst_time": {"type": "integer"},
                    "priority": {"type": "integer"},
                },
                "required": ["pid", "arrival_time", "burst_time"],
            },
        },
        "algorithms": {
            "type": "array",
            "items": {"type": "string", "enum": list(CPU_ALGO_API)},
        },
        "quantum": {"type": "integer"},
        "remove_pid": {"type": "string"},
    },
    "required": ["message", "action"],
}

WELCOME = (
    "Hi! I'm your scheduling assistant. Describe your CPU workload in plain "
    "English and I'll build the process list for you — no forms needed.\n\n"
    "Try:\n"
    "- `P1 arrival 0 burst 5, P2 arrival 2 burst 3, P3 arrival 4 burst 8`\n"
    "- `use round robin with quantum 2 and run it`\n"
    "- `remove P2` · `clear` · `show` · `help`"
)

SYSTEM_PROMPT = """You are the INPUT PARSER for an OS CPU-scheduling simulator.
You DO NOT calculate scheduling results, schedules, or metrics for a workload — a
separate backend does that. Your job is to turn the user's message into one JSON
action object. You MAY explain scheduling CONCEPTS in plain English.

Reply with a SINGLE JSON object and nothing else (no prose, no code fences). Use
EXACTLY these keys (omit optional ones you don't need):
{
  "message": "<one short friendly sentence to the user>",
  "action": "add" | "clear" | "remove" | "run" | "explain" | "none",
  "processes": [{"pid": "P1", "arrival_time": 0, "burst_time": 5}],
  "algorithms": ["FCFS", "SJF Non-Preemptive"],
  "quantum": 2,
  "remove_pid": "P2"
}

"algorithms" is a LIST of zero or more canonical names, EXACTLY from this set
(never an abbreviation like "SJF"):
  "FCFS", "SJF Non-Preemptive", "SJF Preemptive", "Round Robin",
  "Priority Non-Preemptive", "Priority Preemptive"

Rules:
- Only include processes the user EXPLICITLY described. NEVER invent numbers.
- Omit "priority" unless the user gave one.
- "run"/"simulate"/"solve"/"compare"/"provide the results" => action "run".
- Just adding processes => "add". Clearing the list => "clear".
- Removing one => "remove" with "remove_pid" (e.g. "P2").
- The user may name MULTIPLE algorithms (e.g. "by FCFS and SJF") — list them ALL
  in "algorithms". Set "quantum" whenever the user mentions one.
- If the user asks a CONCEPT question (e.g. "what is SJF", "difference between
  FCFS and Round Robin") and does NOT ask to run, use action "explain" and put a
  short, correct explanation in "message".
- If required info is missing (e.g. Round Robin needs a quantum), use action
  "none" and ask for it in "message".
- "message" must NEVER contain a computed schedule, execution order, or metric
  numbers for the user's specific workload — those come ONLY from the backend.

CRITICAL:
- "processes" must contain ONLY processes described in the user's LATEST message;
  use [] or omit if none. NEVER reuse processes from earlier example messages.
- Set "action":"run" ONLY if the user explicitly asks to run/simulate/solve/compare.
  Otherwise use "add" (when processes are given), "explain", or "none"."""

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
        },
    )
    + _ex(
        "use round robin with quantum 3 and run it",
        {
            "message": "Running Round Robin with quantum 3.",
            "action": "run",
            "algorithms": ["Round Robin"],
            "quantum": 3,
        },
    )
    + _ex(
        "P1 burst 3 arrival 1, P2 burst 4 arrival 2, P3 burst 5 arrival 3, by FCFS and SJF provide the results",
        {
            "message": "Comparing FCFS and SJF Non-Preemptive on your three processes.",
            "action": "run",
            "processes": [
                {"pid": "P1", "arrival_time": 1, "burst_time": 3},
                {"pid": "P2", "arrival_time": 2, "burst_time": 4},
                {"pid": "P3", "arrival_time": 3, "burst_time": 5},
            ],
            "algorithms": ["FCFS", "SJF Non-Preemptive"],
        },
    )
    + _ex(
        "what's the difference between FCFS and Round Robin?",
        {
            "message": "FCFS runs each process to completion in arrival order, so a "
            "long early job can delay everyone (convoy effect). Round Robin gives "
            "each process a fixed time slice in turn, improving responsiveness at "
            "the cost of more context switches.",
            "action": "explain",
        },
    )
    + _ex(
        "remove P3",
        {
            "message": "Removed P3.",
            "action": "remove",
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


def _run_many(algorithms, processes, quantum):
    """Run each algorithm on the SAME workload via the backend.

    Returns `{algorithm: result}`. Loops the per-algorithm endpoints (not
    `/schedule/analyze`) so each result carries the full `schedule`/`timeline`
    the comparison + explanation rely on. Backend/connection errors propagate to
    the caller, which reports them like `_run_and_report`.
    """
    return {algo: _run_simulation(algo, processes, quantum) for algo in algorithms}


def _compare_md(results_by_algo):
    """Markdown comparison table across algorithms, in `_result_md` style."""
    header = "| Algorithm | Avg Waiting | Avg Turnaround | CPU Util | Execution order |"
    rows = [header, "|---|---|---|---|---|"]
    for algo, r in results_by_algo.items():
        order = " → ".join(b["pid"] for b in r.get("schedule", []))
        rows.append(
            f"| {algo} | {r.get('avg_waiting_time', 0):.2f} "
            f"| {r.get('avg_turnaround_time', 0):.2f} "
            f"| {r.get('cpu_utilization', 0):.2f}% | {order} |"
        )
    table = "\n".join(rows)
    return f"**Comparison** ✅\n\n{table}\n\n_Open the **Compare** page for the full Gantt charts._"


def _explain_results(results_by_algo):
    """Plain-English explanation of a comparison — grounded in the REAL numbers.

    Names the winner per metric (only quoting values present in backend results)
    and adds 1–2 qualitative concept notes (convoy effect, RR overhead, SJF
    optimality). Never invents or derives numbers the backend didn't return.
    """
    if len(results_by_algo) < 2:
        return ""

    best_wait = min(
        results_by_algo.items(), key=lambda kv: kv[1].get("avg_waiting_time", float("inf"))
    )
    best_tat = min(
        results_by_algo.items(), key=lambda kv: kv[1].get("avg_turnaround_time", float("inf"))
    )

    lines = ["**Why:**"]
    lines.append(
        f"- **{best_wait[0]}** has the lowest average waiting time "
        f"(**{best_wait[1].get('avg_waiting_time', 0):.2f}**)."
    )
    if best_tat[0] == best_wait[0]:
        lines.append(
            f"- It also gives the lowest average turnaround time "
            f"(**{best_tat[1].get('avg_turnaround_time', 0):.2f}**)."
        )
    else:
        lines.append(
            f"- **{best_tat[0]}** has the lowest average turnaround time "
            f"(**{best_tat[1].get('avg_turnaround_time', 0):.2f}**)."
        )

    notes = []
    if best_wait[0].startswith("SJF"):
        notes.append(
            "SJF minimises average waiting time by running shorter bursts first."
        )
    if "FCFS" in results_by_algo and best_wait[0] != "FCFS":
        notes.append(
            "FCFS serves processes in arrival order, so a long early job can delay "
            "shorter ones (convoy effect) — pushing its average waiting time up."
        )
    if "Round Robin" in results_by_algo and best_wait[0] != "Round Robin":
        notes.append(
            "Round Robin improves responsiveness by time-slicing, but the extra "
            "preemptions tend to raise average waiting time versus a shortest-job policy."
        )
    lines += [f"- {n}" for n in notes]
    return "\n".join(lines)


def _run_multi_and_report(parts, algorithms):
    """Run several algorithms on the current workload; append table + explanation."""
    if not st.session_state.processes:
        parts.append("There are no processes to run yet — describe some first.")
        return
    if "Round Robin" in algorithms and not st.session_state.get("chat_quantum"):
        parts.append("Round Robin needs a quantum. Say e.g. `quantum 2`.")
        return
    try:
        results = _run_many(
            algorithms, st.session_state.processes, st.session_state.get("chat_quantum")
        )
        st.session_state.last_algorithm = algorithms[0]
        parts.append(_compare_md(results))
        explanation = _explain_results(results)
        if explanation:
            parts.append(explanation)
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


def _normalize_algos(action: dict):
    """Canonical, de-duplicated algorithm list from the action.

    Accepts the new `algorithms` (list) and the legacy `algorithm` (string), so
    older callers/few-shots keep working. Order is preserved; the first entry
    becomes the sticky algorithm.
    """
    raw = []
    listed = action.get("algorithms")
    if isinstance(listed, list):
        raw.extend(listed)
    elif isinstance(listed, str):
        raw.append(listed)
    legacy = action.get("algorithm")
    if legacy:
        raw.append(legacy)

    out = []
    for value in raw:
        canon = _normalize_algo(value)
        if canon and canon not in out:
            out.append(canon)
    return out


def apply_action(action: dict):
    """Apply a structured action dict; return extra markdown for the reply."""
    parts = []

    algorithms = _normalize_algos(action)
    if algorithms:
        st.session_state.sticky_cpu_algorithm = algorithms[0]
        st.session_state.last_algorithm = algorithms[0]
        if len(algorithms) == 1:
            parts.append(f"Algorithm set to **{algorithms[0]}**.")
        else:
            parts.append("Algorithms set to **" + "**, **".join(algorithms) + "**.")

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
            if len(algorithms) >= 2:
                _run_multi_and_report(parts, algorithms)
            else:
                # 0 named → sticky; 1 named → already set as sticky above.
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
    action = llm.chat_json(_llm_messages(user_text), schema=ACTION_SCHEMA)  # grammar-constrained
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


def detect_algorithms(text):
    """Return ALL algorithms named in the text (plural form of detect_algorithm).

    Lets the offline path handle "by FCFS and SJF" the same way the LLM path does.
    Preemptive/non-preemptive is inferred from the whole message, matching
    detect_algorithm's heuristic.
    """
    t = text.lower()
    pre = "pre" in t and "non" not in t
    found = []

    def add(a):
        if a not in found:
            found.append(a)

    if "fcfs" in t or "first come" in t or "first-come" in t:
        add("FCFS")
    if "sjf" in t or "shortest job" in t:
        add("SJF Preemptive" if pre else "SJF Non-Preemptive")
    if "priority" in t:
        add("Priority Preemptive" if pre else "Priority Non-Preemptive")
    if "round robin" in t or re.search(r"\brr\b", t):
        add("Round Robin")
    return found


# One-line concept blurbs so the offline path can still answer "what is X" /
# "difference between X and Y" questions when no model is installed.
CONCEPTS = {
    "FCFS": "First-Come First-Served runs processes in arrival order, non-preemptively. "
    "Simple and fair by arrival, but a long early job delays everyone (convoy effect).",
    "SJF Non-Preemptive": "Shortest Job First picks the shortest available burst each time "
    "the CPU frees up and runs it to completion. Minimises average waiting time, but long "
    "jobs can starve.",
    "SJF Preemptive": "Shortest Remaining Time First preempts the running process whenever a "
    "shorter job arrives. Best average waiting time, at the cost of more context switches and "
    "possible starvation.",
    "Round Robin": "Each process gets a fixed time quantum in turn, preempting when it expires. "
    "Great responsiveness and fairness; performance depends on the quantum size.",
    "Priority Non-Preemptive": "Runs the highest-priority ready process to completion. Important "
    "work goes first, but low-priority jobs can starve (mitigated by aging).",
    "Priority Preemptive": "Switches to a higher-priority process as soon as it arrives. "
    "Responsive for important work; risks starving low-priority jobs.",
}


def _concept_md(algos):
    """Markdown explanation for one or more named algorithms (offline concept Q&A)."""
    return "\n\n".join(f"**{a}** — {CONCEPTS[a]}" for a in algos if a in CONCEPTS)


def detect_quantum(text):
    m = re.search(r"(?:quantum|time\s*slice|\bq\b)\s*(?:=|:|of)?\s*(\d+)", text, re.I)
    return int(m.group(1)) if m else None


def _wants_run(text):
    # "compare" / "results" cover phrasings like "compare FCFS and SJF" and
    # "provide the results" that mean "run it" but lack an explicit run verb.
    return bool(re.search(r"\b(run|simulate|solve|compute|execute|compare|results?)\b", text, re.I))


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

    algos = detect_algorithms(t)
    quantum = detect_quantum(t)
    procs, skipped = extract_processes(t)

    # Concept Q&A: algorithms named with nothing to run on (no new processes and
    # none stored), or an explicit concept question — explain instead of acting.
    is_concept_q = bool(
        re.search(r"\b(what|which|explain|difference|differ|describe|how does)\b", low)
    )
    if algos and not procs and (is_concept_q or not st.session_state.processes):
        return _concept_md(algos), "Here's a quick explanation."

    parts = []
    if algos:
        st.session_state.sticky_cpu_algorithm = algos[0]
        st.session_state.last_algorithm = algos[0]
        if len(algos) == 1:
            parts.append(f"Algorithm set to **{algos[0]}**.")
        else:
            parts.append("Algorithms set to **" + "**, **".join(algos) + "**.")
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
        if len(algos) >= 2:
            _run_multi_and_report(parts, algos)
        else:
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
    """Render setup UI for the not-ready states; return (use_llm, status).

    Only the actionable not-ready branches draw anything here (offline-install
    notice, or the download button). When the model is ready this stays silent —
    render_chatbot() shows a compact, hover-to-reveal chip instead of a banner.
    """
    status = llm.runtime_status()

    if not status["llama_installed"]:
        st.warning(
            "**Offline mode** — `llama-cpp-python` isn't installed, so I'm using the "
            "built-in rule-based parser. To enable the full Phi-3 bot, install the CPU "
            "wheel:\n\n"
            "```\npip install llama-cpp-python --extra-index-url "
            "https://abetlen.github.io/llama-cpp-python/whl/cpu\n```"
        )
        return False, status

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
        return False, status

    return True, status


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

    use_llm, status = _render_model_panel()

    top_l, top_r = st.columns([3, 1])
    with top_l:
        # Compact model chip; the full path is concealed and revealed on hover
        # (native browser title tooltip) so it isn't a distracting top banner.
        if use_llm:
            path = html.escape(status.get("model_path") or "")
            st.markdown(
                f"<span title=\"{path}\">🟢 Phi-3</span>",
                unsafe_allow_html=True,
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
