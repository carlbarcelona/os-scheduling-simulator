# frontend/app.py
import streamlit as st
import requests
import json
from config import *

# -- Page config (must be first Streamlit call)
st.set_page_config(
    page_title="OS Scheduling Simulator",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Session state initialization
if "processes" not in st.session_state:
    st.session_state.processes = []

# Pending input resets — must run BEFORE the widgets that own these keys are
# instantiated. Streamlit forbids setting st.session_state[key] after a widget
# with that key has already rendered in the current run, so the previous
# approach (clearing keys right before st.rerun(), at the bottom of the script)
# failed: the widgets had already been created earlier in that same run, and
# the rerun re-executes the whole script — the clear was always "too late" by
# definition. Instead, queue the reset and apply it here, at the top, before
# anything else touches these keys.
if st.session_state.get("_reset_scheduler_inputs"):
    st.session_state.pid_input = ""
    st.session_state.arrival_input = 0
    st.session_state.burst_input = 1
    st.session_state.priority_input = 0
    st.session_state._reset_scheduler_inputs = False

if st.session_state.get("_reset_memory_inputs"):
    st.session_state.m_pid_input = ""
    st.session_state.m_size_input = 1
    st.session_state.m_burst_input = 1
    st.session_state._reset_memory_inputs = False

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "last_algorithm" not in st.session_state:
    st.session_state.last_algorithm = None

if "compare_results" not in st.session_state:
    st.session_state.compare_results = None

if "disk_response" not in st.session_state:
    st.session_state.disk_response = None

if "disk_compare_results" not in st.session_state:
    st.session_state.disk_compare_results = None

if "memory_response" not in st.session_state:
    st.session_state.memory_response = None

if "vm_response" not in st.session_state:
    st.session_state.vm_response = None

if "memory_processes" not in st.session_state:
    st.session_state.memory_processes = []

if "disk_params" not in st.session_state:
    st.session_state.disk_params = {
        "head": 0,
        "number_of_tracks": 1,
        "direction": "right",
        "requests_input": "",
    }

if "disk_params_set" not in st.session_state:
    st.session_state.disk_params_set = False

if "last_disk_algorithm" not in st.session_state:
    st.session_state.last_disk_algorithm = None

# -- "Sticky" selections that must survive page navigation --
# Streamlit deletes a widget's key from session_state on any run where that
# widget isn't rendered (e.g. the user is on a different page), then recreates
# it fresh — with its default value — the next time it IS rendered. A plain
# key= is therefore not enough for state that should outlive a trip to another
# page. The fix is to mirror each such value into its own always-alive
# session_state entry, then pass that as the widget's `index`/initial value
# every time the widget is (re)created, and update the mirror right after.
if "sticky_cpu_algorithm" not in st.session_state:
    st.session_state.sticky_cpu_algorithm = "FCFS"

if "sticky_disk_algorithm" not in st.session_state:
    st.session_state.sticky_disk_algorithm = "FCFS"

if "sticky_fit_strategy" not in st.session_state:
    st.session_state.sticky_fit_strategy = "first"

if "sticky_compaction" not in st.session_state:
    st.session_state.sticky_compaction = "With Compaction"

if "sticky_vm_algorithm" not in st.session_state:
    st.session_state.sticky_vm_algorithm = "FIFO"

# -- SIDEBAR NAVIGATION
st.sidebar.title("⚙️ OS Scheduling Simulator")
st.sidebar.caption("OS Scheduling Algorithm Visualizer")

# Top-level input mode: the conversational Chatbot vs the manual form-driven
# pages. The chatbot stays a self-contained module — this only mounts it; all
# chat/LLM logic lives in chatbot.py / llm.py.
mode = st.sidebar.segmented_control(
    "Mode", ["Manual", "Chatbot"], default="Manual", label_visibility="collapsed"
)
st.sidebar.divider()

if mode == "Chatbot":
    from chatbot import render_chatbot  # lazy: only load the bot/llm when used
    render_chatbot()
    st.stop()  # halt here so the manual pages below don't render in chat mode

page = st.sidebar.radio(
    "Navigate",
    ["Scheduler", "Mass Storage", "Memory", "Virtual Memory", "Compare", "Recommend"],
    label_visibility="collapsed"
)

st.sidebar.divider()

# -------------------------------------------------------------
# PAGE: SCHEDULER
# -------------------------------------------------------------
if page == "Scheduler":

    CPU_ALGORITHMS = ["FCFS", "SJF Non-Preemptive", "SJF Preemptive", "Round Robin", "Priority Non-Preemptive", "Priority Preemptive"]
    algorithm = st.sidebar.selectbox(
        "Algorithm",
        CPU_ALGORITHMS,
        index=CPU_ALGORITHMS.index(st.session_state.sticky_cpu_algorithm),
        key="cpu_algorithm_select",
        help="Select the CPU scheduling algorithm to simulate."
    )

    # Per-algorithm process queue: switching algorithms resets the process list,
    # since different algorithms expect differently-shaped process data (e.g.
    # Priority needs a priority field, others don't) and old results no longer
    # correspond to the newly selected algorithm.
    if algorithm != st.session_state.sticky_cpu_algorithm:
        st.session_state.processes = []
        st.session_state.last_response = None
        st.session_state.compare_results = None

    st.session_state.sticky_cpu_algorithm = algorithm

    # Keep last_algorithm in sync with the CURRENT selection, not just the last
    # successful run — this is what lets the Compare page reflect "right now"
    # on the Scheduler page (e.g. switching to Round Robin immediately unlocks
    # CPU Compare's full comparison, even before clicking Run).
    st.session_state.last_algorithm = algorithm

    quantum = None
    if algorithm == "Round Robin":
        quantum = st.sidebar.number_input(
            "Quantum",
            min_value=1, step=1, value=2,
            key="quantum_input",
            help="Time slice allocated to each process in Round Robin."
        )

    st.sidebar.divider()

    st.sidebar.subheader("Add Process")

    col_pid, col_at = st.sidebar.columns(2)
    with col_pid:
        pid = st.text_input("Process ID", placeholder="e.g. P1", label_visibility="visible", key="pid_input")
    with col_at:
        arrival_time = st.number_input("Arrival", min_value=0, step=1, key="arrival_input")

    col_bt, col_pr = st.sidebar.columns(2)
    with col_bt:
        burst_time = st.number_input("Burst", min_value=1, step=1, key="burst_input")

    priority = 0
    if algorithm in ["Priority Non-Preemptive", "Priority Preemptive"]:
        with col_pr:
            priority = st.number_input("Priority", min_value=0, step=1, value=0, key="priority_input", help="Lower number = higher priority.")
    else:
        with col_pr:
            st.empty()

    if st.sidebar.button("＋ Add Process", use_container_width=True, type="primary"):
        if not pid.strip():
            st.sidebar.error("Process ID cannot be empty.")
        elif any(p["pid"] == pid.strip() for p in st.session_state.processes):
            st.sidebar.error(f"PID '{pid}' already exists.")
        else:
            process = {
                "pid": pid.strip(),
                "arrival_time": int(arrival_time),
                "burst_time": int(burst_time),
            }
            if algorithm in ["Priority Non-Preemptive", "Priority Preemptive"]:
                process["priority"] = int(priority)
            st.session_state.processes.append(process)
            st.toast(f"Added {pid.strip()}", icon="✅")
            # Queue the input reset — applied at the top of the script on the
            # next run, before these widgets are instantiated (see top of file).
            st.session_state._reset_scheduler_inputs = True
            st.rerun()

    st.sidebar.divider()

    if st.session_state.processes:
        st.sidebar.subheader(f"Process Queue — {len(st.session_state.processes)}")
        for i, p in enumerate(st.session_state.processes):
            col_info, col_del = st.sidebar.columns([4, 1])
            with col_info:
                if "priority" in p:
                    st.caption(f"**{p['pid']}** · AT:{p['arrival_time']} · BT:{p['burst_time']} · PR:{p['priority']}")
                else:
                    st.caption(f"**{p['pid']}** · AT:{p['arrival_time']} · BT:{p['burst_time']}")
            with col_del:
                if st.button("✕", key=f"del_{i}", help=f"Remove {p['pid']}"):
                    st.session_state.processes.pop(i)
                    st.session_state.last_response = None
                    st.rerun()

        if st.sidebar.button("🗑️ Clear All", use_container_width=True):
            st.session_state.processes = []
            st.session_state.last_response = None
            st.session_state.compare_results = None
            st.rerun()

    st.title("CPU Scheduler")
    st.caption(f"Algorithm: **{algorithm}** · Processes: **{len(st.session_state.processes)}**")
    st.divider()

    ALGORITHM_MAP = {
        "FCFS": FCFS_API,
        "SJF Non-Preemptive": SJF_NP_API,
        "SJF Preemptive": SJF_PRE_API,
        "Round Robin": ROUND_ROBIN_API,
        "Priority Non-Preemptive": PRIORITY_NP_API,
        "Priority Preemptive": PRIORITY_PRE_API,
    }

    # Cached API call wrapper (Week 3: @st.cache_data)
    # processes_json is json.dumps(processes) - hashable for cache key
    @st.cache_data
    def run_simulation(endpoint: str, processes_json: str, quantum_value=None):
        payload = {"processes": json.loads(processes_json)}
        if quantum_value is not None:
            payload["quantum"] = quantum_value
        response = requests.post(endpoint, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()

    run_clicked = st.sidebar.button(
        f"▶ Run {algorithm}",
        type="primary",
        use_container_width=True,
        disabled=len(st.session_state.processes) == 0,
    )

    if run_clicked:
        processes_json = json.dumps(st.session_state.processes)
        q = int(quantum) if (algorithm == "Round Robin" and quantum) else None

        with st.status(f"Running {algorithm}...", expanded=True) as status:
            try:
                st.write("Sending request to API...")
                st.session_state.last_response = run_simulation(
                    ALGORITHM_MAP[algorithm], processes_json, q
                )
                st.session_state.last_algorithm = algorithm
                st.write("Response received.")
                status.update(label="Simulation complete!", state="complete", expanded=False)
                st.toast("Simulation complete!", icon="✅")

            except requests.exceptions.Timeout:
                status.update(label="Request timed out.", state="error", expanded=False)
                st.error("Request timed out. Is the backend running?")
                st.session_state.last_response = None

            except requests.exceptions.HTTPError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                status.update(label="API error.", state="error", expanded=False)
                st.error(f"API error: {detail}")
                st.session_state.last_response = None

            except requests.exceptions.ConnectionError:
                status.update(label="Cannot connect to API.", state="error", expanded=False)
                st.error("Cannot connect to the API. Is the backend running?")
                st.session_state.last_response = None

    if st.session_state.last_response is not None:
        st.divider()
        result = st.session_state.last_response

        tab_metrics, tab_gantt, tab_raw = st.tabs(["Metrics", "Gantt Chart", "Raw Response"])

        with tab_metrics:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(
                    "Avg Waiting Time",
                    f"{result.get('avg_waiting_time', 0):.2f}",
                    help="Average time each process spends waiting in the ready queue before execution."
                )
            with m2:
                st.metric(
                    "Avg Turnaround Time",
                    f"{result.get('avg_turnaround_time', 0):.2f}",
                    help="Average total time from process arrival to completion (waiting + execution)."
                )
            with m3:
                st.metric(
                    "CPU Utilization",
                    f"{result.get('cpu_utilization', 0):.2f}%",
                    help="Percentage of total time the CPU was actively executing a process (not idle)."
                )

            st.divider()

            # Per-process metrics table
            # NOTE: This is a TEMPORARY frontend-side calculation.
            # The backend (ScheduleResult/ScheduledProcess in schemas.py) currently only
            # returns avg_waiting_time / avg_turnaround_time / cpu_utilization, not
            # per-process waiting/turnaround values - even though the algorithm
            # functions compute these internally before returning.
            # Ideally, the backend should expose per-process "waiting" and "turnaround"
            # fields in ScheduledProcess so the frontend only displays, not computes.
            # Flagged to Architect/Algorithm Engineer for schemas.py update.
            st.subheader("Process Metrics")

            schedule = result.get("schedule", [])
            process_lookup = {p["pid"]: p for p in st.session_state.processes}

            table_rows = []
            total_waiting = 0
            total_turnaround = 0
            for entry in schedule:
                pid_entry = entry["pid"]
                start = entry["start"]
                finish = entry["end"]
                proc = process_lookup.get(pid_entry, {})
                arrival = proc.get("arrival_time", 0)
                burst = proc.get("burst_time", finish - start)
                turnaround = finish - arrival
                waiting = turnaround - burst
                total_waiting += waiting
                total_turnaround += turnaround
                table_rows.append({
                    "PID": pid_entry,
                    "Arrival": arrival,
                    "Burst": burst,
                    "Start": start,
                    "Finish": finish,
                    "Waiting": waiting,
                    "Turnaround": turnaround,
                })

            if table_rows:
                n = len(table_rows)
                table_rows.append({
                    "PID": "AVG",
                    "Arrival": "",
                    "Burst": "",
                    "Start": "",
                    "Finish": "",
                    "Waiting": round(total_waiting / n, 2),
                    "Turnaround": round(total_turnaround / n, 2),
                })
                st.dataframe(table_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No schedule data to display.")

        with tab_gantt:
            from components.gantt import render_gantt
            gantt_layout = st.segmented_control(
                "Layout",
                ["Single lane", "Per process"],
                default="Single lane",
                key="cpu_gantt_layout",
                label_visibility="collapsed",
                help="Single lane = classic CPU timeline; Per process = one row per process.",
            )
            layout_arg = "per_process" if gantt_layout == "Per process" else "single"
            st.plotly_chart(
                render_gantt(result["timeline"], result["schedule"], layout=layout_arg),
                use_container_width=True,
            )

        with tab_raw:
            st.json(result)

# -------------------------------------------------------------
# PAGE: MASS STORAGE
# -------------------------------------------------------------
elif page == "Mass Storage":
    st.session_state.disk_params_set = True
    st.title("Mass Storage — Disk Scheduling")
    st.caption("Module 7 — Disk head scheduling algorithms")
    st.divider()

    st.sidebar.subheader("Disk Parameters")

    DISK_ALGORITHMS = ["FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"]
    disk_algorithm = st.sidebar.selectbox(
        "Algorithm",
        DISK_ALGORITHMS,
        index=DISK_ALGORITHMS.index(st.session_state.sticky_disk_algorithm),
        key="disk_algorithm_select",
        help="Select the disk scheduling algorithm."
    )

    # Stale results from a different algorithm shouldn't linger on screen once
    # the selection changes — the displayed result should always match what's
    # currently selected.
    if disk_algorithm != st.session_state.sticky_disk_algorithm:
        st.session_state.disk_response = None

    st.session_state.sticky_disk_algorithm = disk_algorithm

    head = st.sidebar.number_input(
        "Initial Head Position",
        min_value=0, step=1, value=st.session_state.disk_params["head"],
        help="Starting position of the disk head."
    )
    st.session_state.disk_params["head"] = head

    number_of_tracks = st.sidebar.number_input(
        "Number of Tracks",
        min_value=1, step=1, value=st.session_state.disk_params["number_of_tracks"],
        help="Total number of cylinders on the disk."
    )
    st.session_state.disk_params["number_of_tracks"] = number_of_tracks

    # Direction only matters for SCAN, C-SCAN, LOOK, C-LOOK — FCFS and SSTF have no directional sweep
    direction = "right"
    if disk_algorithm in ["SCAN", "C-SCAN", "LOOK", "C-LOOK"]:
        direction = st.sidebar.selectbox(
            "Direction",
            ["right", "left"],
            index=["right", "left"].index(st.session_state.disk_params["direction"]),
            key="disk_direction_select",
            help="Initial direction of head movement."
        )
        st.session_state.disk_params["direction"] = direction

    st.sidebar.divider()
    st.sidebar.subheader("Disk Requests")
    st.sidebar.caption("Enter cylinder numbers separated by commas.")
    requests_input = st.sidebar.text_input(
        "Requests",
        value=st.session_state.disk_params["requests_input"],
        placeholder="e.g. 98, 183, 37, 122",
        label_visibility="collapsed"
    )
    st.session_state.disk_params["requests_input"] = requests_input

    try:
        requests_list = [int(r.strip()) for r in requests_input.split(",") if r.strip()]
    except ValueError:
        st.sidebar.error("Invalid input — enter comma-separated integers only.")
        requests_list = []

    st.sidebar.divider()
    disk_run_clicked = st.sidebar.button(
        f"▶ Run {disk_algorithm}",
        use_container_width=True,
        type="primary",
        disabled=len(requests_list) == 0,
    )

    DISK_ALGORITHM_MAP = {
        "FCFS": DISK_FCFS_API,
        "SSTF": DISK_SSTF_API,
        "SCAN": DISK_SCAN_API,
        "C-SCAN": DISK_CSCAN_API,
        "LOOK": DISK_LOOK_API,
        "C-LOOK": DISK_CLOOK_API,
    }

    st.subheader(f"Algorithm: {disk_algorithm}")

    if disk_run_clicked:
        payload = {
            "head": int(head),
            "requests": requests_list,
            "number_of_tracks": int(number_of_tracks),
            "direction": direction,
        }

        with st.status(f"Running {disk_algorithm}...", expanded=True) as status:
            try:
                st.write("Sending request to API...")
                response = requests.post(
                    DISK_ALGORITHM_MAP[disk_algorithm],
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
                st.session_state.disk_response = response.json()
                st.session_state.last_disk_algorithm = disk_algorithm
                st.write("Response received.")
                status.update(label="Simulation complete!", state="complete", expanded=False)
                st.toast("Simulation complete!", icon="✅")

            except requests.exceptions.Timeout:
                status.update(label="Request timed out.", state="error", expanded=False)
                st.error("Request timed out. Is the backend running?")
                st.session_state.disk_response = None

            except requests.exceptions.HTTPError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                status.update(label="API error.", state="error", expanded=False)
                st.error(f"API error: {detail}")
                st.session_state.disk_response = None

            except requests.exceptions.ConnectionError:
                status.update(label="Cannot connect to API.", state="error", expanded=False)
                st.error("Cannot connect to the API. Is the backend running?")
                st.session_state.disk_response = None

    if st.session_state.disk_response is not None:
        st.divider()
        disk_result = st.session_state.disk_response

        tab_summary, tab_movements, tab_raw = st.tabs(["Summary", "Head Movements", "Raw Response"])

        with tab_summary:
            c1, c2 = st.columns(2)
            with c1:
                st.metric(
                    "Total Head Movement",
                    f"{disk_result.get('total_head_movement', 0)}",
                    help="Total distance the disk head traveled to service all requests."
                )
            with c2:
                st.metric(
                    "Initial Head Position",
                    f"{disk_result.get('initial_head', 0)}",
                    help="Starting position of the disk head."
                )

            st.divider()

            # Seek pattern visualization — Plotly line chart
            # Matches OS textbook standard: cylinder position on X-axis,
            # time/step on Y-axis going downward (top = step 0, bottom = last step)
            #
            # Two INDEPENDENT display rules (confirmed against the OS textbook
            # diagram, not inferred from numbers alone — these are properties of
            # the ALGORITHM, not something derivable from the sequence values):
            #   1. "?" LABELING — only algorithms that physically sweep all the
            #      way to a disk boundary (SCAN, C-SCAN) show that boundary point
            #      labeled "?" instead of its real track number. LOOK/C-LOOK
            #      never touch the physical edge (they reverse/jump at the
            #      farthest REQUEST), so this never applies to them.
            #   2. DASHING — reserved specifically for the "C" algorithms'
            #      wraparound jump (C-SCAN, C-LOOK), where the head leaves one
            #      end of the disk and reappears elsewhere without passing
            #      through the space between. A plain reversal-in-place (SCAN,
            #      LOOK changing direction) is continuous physical movement and
            #      stays solid even though nothing is serviced exactly at the
            #      turn point.
            # These two rules are independent — SCAN gets "?" but never dashes;
            # C-LOOK dashes but never shows "?" (it has no edge visit at all).
            st.subheader("Seek Pattern")
            sequence = disk_result.get("sequence", [])
            if sequence:
                import plotly.graph_objects as go

                EDGE_TOUCHING_ALGOS = {"SCAN", "C-SCAN"}
                JUMP_ALGOS = {"C-SCAN", "C-LOOK"}
                touches_edge = disk_algorithm in EDGE_TOUCHING_ALGOS
                is_jump_algo = disk_algorithm in JUMP_ALGOS

                # Backward-compat: the current real backend still emits literal
                # "?" strings in sequence for C-SCAN (a known bug — see disk
                # algorithm notes). Resolve those to real numeric positions
                # first, so the rest of this logic only ever deals with
                # numbers — "?" becomes purely a DISPLAY LABEL we compute
                # ourselves below, never a value baked into the data.
                max_track = number_of_tracks - 1
                # Resolve "?" runs POSITIONALLY, not independently per-index —
                # a run of consecutive "?" (C-SCAN emits exactly two) means:
                # the FIRST one in the run = the edge being approached, the
                # LAST one = the edge being departed from after the wrap.
                # Resolving each "?" independently from its immediate neighbors
                # breaks when a neighbor is ALSO still "?" (unresolved) at the
                # time you look at it — both placeholders in a 2-long run would
                # otherwise see the same surrounding real values and resolve
                # identically, which is wrong.
                numeric_sequence = list(sequence)
                i = 0
                while i < len(numeric_sequence):
                    if numeric_sequence[i] == "?":
                        run_start = i
                        while i < len(numeric_sequence) and numeric_sequence[i] == "?":
                            i += 1
                        run_end = i  # exclusive
                        prev_real = numeric_sequence[run_start - 1] if run_start > 0 else 0
                        next_real = numeric_sequence[run_end] if run_end < len(numeric_sequence) else max_track
                        entry_edge = max_track if prev_real >= (max_track / 2) else 0
                        exit_edge = max_track if next_real >= (max_track / 2) else 0
                        for j in range(run_start, run_end):
                            numeric_sequence[j] = entry_edge if j == run_start else exit_edge
                    else:
                        i += 1

                # Find the single reversal point: first index where the sweep
                # direction flips. C-SCAN/C-LOOK have exactly one (the jump);
                # SCAN/LOOK have exactly one too (the in-place turn); FCFS/SSTF
                # may have none, or several (they're not monotonic sweeps at
                # all) — in that case there's nothing to dash or label anyway.
                direction_param = disk_result.get("direction", "right")
                reversal_idx = None
                for i in range(len(numeric_sequence) - 1):
                    if direction_param == "right" and numeric_sequence[i + 1] < numeric_sequence[i]:
                        reversal_idx = i
                        break
                    if direction_param == "left" and numeric_sequence[i + 1] > numeric_sequence[i]:
                        reversal_idx = i
                        break

                # Build display labels — start from real numbers, override
                # with "?" only at genuine edge-visit points, only for
                # EDGE_TOUCHING_ALGOS.
                display_labels = [str(v) for v in numeric_sequence]
                if touches_edge and reversal_idx is not None:
                    if direction_param == "right" and numeric_sequence[reversal_idx] == max_track:
                        display_labels[reversal_idx] = "?"
                    elif direction_param == "left" and numeric_sequence[reversal_idx] == 0:
                        display_labels[reversal_idx] = "?"
                    # The point right after a wrap (C-SCAN only) may be the
                    # opposite boundary too, if no real request sits there.
                    if reversal_idx + 1 < len(numeric_sequence):
                        nxt = numeric_sequence[reversal_idx + 1]
                        original_requests = disk_result.get("requests", [])
                        if direction_param == "right" and nxt == 0 and 0 not in original_requests:
                            display_labels[reversal_idx + 1] = "?"
                        elif direction_param == "left" and nxt == max_track and max_track not in original_requests:
                            display_labels[reversal_idx + 1] = "?"

                fig = go.Figure()

                if is_jump_algo and reversal_idx is not None:
                    # Split into solid-before, dashed-jump, solid-after.
                    before = [(v, s) for s, v in enumerate(numeric_sequence) if s <= reversal_idx]
                    after = [(v, s) for s, v in enumerate(numeric_sequence) if s > reversal_idx]

                    if before:
                        fig.add_trace(go.Scatter(
                            x=[p[0] for p in before],
                            y=[p[1] for p in before],
                            mode="lines+markers",
                            line=dict(color="#00ff9d", width=2),
                            marker=dict(size=8, color="#00ff9d", symbol="circle"),
                            text=[display_labels[p[1]] for p in before],
                            hovertemplate="%{text}<extra></extra>",
                            showlegend=False,
                        ))

                    if before and after:
                        fig.add_trace(go.Scatter(
                            x=[before[-1][0], after[0][0]],
                            y=[before[-1][1], after[0][1]],
                            mode="lines",
                            line=dict(color="#00ff9d", width=2, dash="dash"),
                            showlegend=False,
                        ))

                    if after:
                        fig.add_trace(go.Scatter(
                            x=[p[0] for p in after],
                            y=[p[1] for p in after],
                            mode="lines+markers",
                            line=dict(color="#00ff9d", width=2),
                            marker=dict(size=8, color="#00ff9d", symbol="circle"),
                            text=[display_labels[p[1]] for p in after],
                            hovertemplate="%{text}<extra></extra>",
                            showlegend=False,
                        ))
                else:
                    # FCFS, SSTF, SCAN, LOOK — single continuous solid path,
                    # even if it touches the edge (SCAN) or reverses (LOOK).
                    fig.add_trace(go.Scatter(
                        x=numeric_sequence,
                        y=list(range(len(numeric_sequence))),
                        mode="lines+markers",
                        line=dict(color="#00ff9d", width=2),
                        marker=dict(size=8, color="#00ff9d", symbol="circle"),
                        text=display_labels,
                        hovertemplate="%{text}<extra></extra>",
                        showlegend=False,
                    ))

                # Override the x-axis tick at the edge position to show "?"
                # instead of the real number, for algorithms that touch the
                # edge — purely a label swap, the point's true plotted
                # position is unchanged.
                tickvals, ticktext = None, None
                if touches_edge:
                    edge_val = max_track if direction_param == "right" else 0
                    base_ticks = sorted(set(numeric_sequence) | {0, max_track})
                    tickvals = base_ticks
                    ticktext = ["?" if t == edge_val else str(t) for t in base_ticks]

                fig.update_layout(
                    xaxis_title="Cylinder Position",
                    yaxis_title="Step",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(
                        gridcolor="#2a2d3e",
                        range=[0, number_of_tracks],
                        tickvals=tickvals,
                        ticktext=ticktext,
                    ),
                    yaxis=dict(gridcolor="#2a2d3e", autorange="reversed"),
                    showlegend=False,
                    margin=dict(l=40, r=20, t=20, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)
                if is_jump_algo and reversal_idx is not None:
                    st.caption("Dashed segment = wraparound jump (no service along the way), solid = servicing requests.")
                elif touches_edge:
                    st.caption("'?' marks the disk boundary the sweep reaches — head physically travels there and reverses in place (no jump).")

        with tab_movements:
            movements = disk_result.get("movements", [])
            if movements:
                st.dataframe(movements, use_container_width=True, hide_index=True)
            else:
                st.info("No movement data available.")

        with tab_raw:
            st.json(disk_result)

# -------------------------------------------------------------
# PAGE: MEMORY
# -------------------------------------------------------------
elif page == "Memory":
    st.title("Memory Management")
    st.caption("Module 5 — MVT (Variable Partition) memory allocation with/without compaction")
    st.divider()

    # Sidebar inputs
    st.sidebar.subheader("Memory Parameters")

    total_memory = st.sidebar.number_input(
        "Total Memory (K)",
        min_value=1, step=64, value=1,
        key="total_memory_input",
        help="Total memory capacity in kilobytes."
    )

    FIT_STRATEGIES = ["first", "best", "worst", "next"]
    fit_strategy = st.sidebar.selectbox(
        "Fit Strategy",
        FIT_STRATEGIES,
        index=FIT_STRATEGIES.index(st.session_state.sticky_fit_strategy),
        key="fit_strategy_select",
        help="Memory allocation strategy. First Fit, Best Fit, Worst Fit, or Next Fit."
    )

    # KNOWN BACKEND GAP: mvt.py's find_fit() only branches on "best"/"worst" —
    # "next" falls through to the same behavior as "first" (always searches
    # from the start of the block list, never resumes from the last
    # allocation point). Selecting Next Fit currently produces IDENTICAL
    # results to First Fit, silently — no error, just a quietly wrong
    # strategy. Flagged to whoever owns mvt.py; not something app.py can
    # work around, since the backend never receives or could derive "where
    # the last search left off" from a single stateless request anyway.
    if fit_strategy == "next":
        st.sidebar.caption("⚠️ Next Fit currently behaves identically to First Fit on the backend (not yet distinctly implemented).")

    # Per-algorithm process queue: switching fit strategy resets the process
    # list, same as the Scheduler page — old results no longer correspond to
    # the newly selected strategy.
    if fit_strategy != st.session_state.sticky_fit_strategy:
        st.session_state.memory_processes = []
        st.session_state.memory_response = None

    st.session_state.sticky_fit_strategy = fit_strategy

    COMPACTION_OPTIONS = ["With Compaction", "Without Compaction"]
    compaction = st.sidebar.selectbox(
        "Compaction",
        COMPACTION_OPTIONS,
        index=COMPACTION_OPTIONS.index(st.session_state.sticky_compaction),
        key="compaction_select",
        help="Whether to compact memory when allocation fails."
    )
    st.session_state.sticky_compaction = compaction

    st.sidebar.divider()
    st.sidebar.subheader("Add Process")

    col_mpid, col_msize = st.sidebar.columns(2)
    with col_mpid:
        m_pid = st.text_input("Process ID", placeholder="e.g. P1", key="m_pid_input")
    with col_msize:
        m_size = st.number_input("Size (K)", min_value=1, step=1, value=1, key="m_size_input")

    m_burst = st.sidebar.number_input(
        "Burst Time",
        min_value=1, step=1, value=1,
        key="m_burst_input",
        help="Estimated execution time of the process."
    )

    if st.sidebar.button("＋ Add Process", use_container_width=True, type="primary", key="m_add_btn"):
        if not m_pid.strip():
            st.sidebar.error("Process ID cannot be empty.")
        elif any(p["pid"] == m_pid.strip() for p in st.session_state.memory_processes):
            st.sidebar.error(f"PID '{m_pid}' already exists.")
        else:
            st.session_state.memory_processes.append({
                "pid": m_pid.strip(),
                "size": int(m_size),
                "burst_time": float(m_burst),
            })
            st.toast(f"Added {m_pid.strip()}", icon="✅")
            st.session_state._reset_memory_inputs = True
            st.rerun()

    st.sidebar.divider()

    if st.session_state.memory_processes:
        st.sidebar.subheader(f"Process Queue — {len(st.session_state.memory_processes)}")
        for i, p in enumerate(st.session_state.memory_processes):
            col_info, col_del = st.sidebar.columns([4, 1])
            with col_info:
                st.caption(f"**{p['pid']}** · Size:{p['size']}K · BT:{p['burst_time']}")
            with col_del:
                if st.button("✕", key=f"m_del_{i}", help=f"Remove {p['pid']}"):
                    st.session_state.memory_processes.pop(i)
                    st.session_state.memory_response = None
                    st.rerun()

        if st.sidebar.button("🗑️ Clear All", use_container_width=True, key="m_clear_btn"):
            st.session_state.memory_processes = []
            st.session_state.memory_response = None
            st.rerun()

    st.sidebar.divider()
    mem_run_clicked = st.sidebar.button(
        "▶ Run Simulation",
        use_container_width=True,
        type="primary",
        disabled=len(st.session_state.memory_processes) == 0,
        key="mem_run_btn"
    )

    # Main area
    st.subheader(f"Strategy: {fit_strategy.capitalize()} Fit — {compaction}")

    if mem_run_clicked:
        mem_payload = {
            "total_memory": int(total_memory),
            "fit_strategy": fit_strategy,
            "processes": st.session_state.memory_processes,
        }

        # Now using the real named constants from config.py (added by the
        # architect) instead of hand-built f-strings — same endpoint paths,
        # but a route rename now only needs a config.py change, not a hunt
        # through app.py for hardcoded URLs.
        mem_endpoint = MEMORY_MVT_WITH_COMPACTION_API if compaction == "With Compaction" else MEMORY_MVT_WITHOUT_COMPACTION_API

        with st.status("Running memory simulation...", expanded=True) as status:
            try:
                st.write("Sending request to API...")
                response = requests.post(mem_endpoint, json=mem_payload, timeout=10)
                response.raise_for_status()
                st.session_state.memory_response = response.json()
                st.write("Response received.")
                status.update(label="Simulation complete!", state="complete", expanded=False)
                st.toast("Simulation complete!", icon="✅")

            except requests.exceptions.Timeout:
                status.update(label="Request timed out.", state="error", expanded=False)
                st.error("Request timed out. Is the backend running?")
                st.session_state.memory_response = None

            except requests.exceptions.HTTPError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                status.update(label="API error.", state="error", expanded=False)
                st.error(f"API error: {detail}")
                st.session_state.memory_response = None

            except requests.exceptions.ConnectionError:
                status.update(label="Cannot connect to API.", state="error", expanded=False)
                st.error("Cannot connect to the API. Is the backend running?")
                st.session_state.memory_response = None

    if st.session_state.memory_response is not None:
        st.divider()
        mem_result = st.session_state.memory_response

        tab_summary, tab_memory_map, tab_timeline, tab_raw = st.tabs(["Summary", "Memory Map", "Timeline", "Raw Response"])

        with tab_summary:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(
                    "Avg Burst Time",
                    f"{mem_result.get('avg_burst_time', 0):.2f}",
                    help="Average execution time across all processes."
                )
            with c2:
                st.metric(
                    "CPU Utilization",
                    f"{mem_result.get('cpu_utilization', 0):.2f}%",
                    help="Percentage of time CPU was actively executing processes."
                )
            with c3:
                st.metric(
                    "Strategy",
                    mem_result.get("strategy", "-").capitalize(),
                    help="Memory fit strategy used."
                )

            st.divider()

            col_alloc, col_fail = st.columns(2)
            with col_alloc:
                st.subheader("Allocated")
                st.dataframe(mem_result.get("allocated", []), use_container_width=True, hide_index=True)
            with col_fail:
                st.subheader("Failed")
                failed = mem_result.get("failed", [])
                if failed:
                    st.dataframe({"PID": failed}, use_container_width=True, hide_index=True)
                else:
                    st.success("All processes allocated successfully.")

            if mem_result.get("compaction_performed"):
                st.info("Compaction was performed to accommodate failed processes.")
                retry = mem_result.get("retry_allocated", [])
                if retry:
                    st.subheader("Retry Allocated (after compaction)")
                    st.dataframe({"PID": retry}, use_container_width=True, hide_index=True)

        with tab_memory_map:
            # Memory block visualization — vertical stacked columns per snapshot
            # Each column = one timeline snapshot, blocks stacked bottom (addr 0) to top (total_memory)
            # Matches standard OS textbook MVT visualization
            st.subheader("Memory State Snapshots")
            st.caption("Each column is a memory snapshot. Blocks stack from address 0 (bottom) upward.")

            timeline = mem_result.get("timeline", [])
            total_mem = mem_result.get("total_memory", 1024)

            if timeline:
                import plotly.graph_objects as go

                # Collect all unique PIDs for consistent color assignment
                all_pids = set()
                for entry in timeline:
                    for block in entry.get("memory_map", []):
                        if not block.get("free", True):
                            all_pids.add(block["pid"])

                # Color palette for processes
                palette = [
                    "#00ff9d", "#3b82f6", "#f59e0b", "#ef4444",
                    "#a855f7", "#06b6d4", "#f97316", "#84cc16",
                ]
                pid_colors = {pid: palette[i % len(palette)] for i, pid in enumerate(sorted(all_pids))}

                # Build one trace per unique PID + FREE
                # x = snapshot index, y = block size, base = block start
                # We need separate traces per PID for legend

                # Collect data per trace
                traces = {}  # key: pid or "FREE"

                for snap_idx, entry in enumerate(timeline):
                    memory_map = entry.get("memory_map", [])
                    event = entry.get("event", "")
                    pid = entry.get("pid")

                    # Build a human-readable label from the real mvt.py event
                    # shapes (confirmed against dev_sched source): "allocated"/
                    # "retry_allocated" carry pid+size, "allocation_failed"/
                    # "removed" carry pid only, "compacted"/"completed" carry
                    # neither. Raw event strings alone ("3: allocation_failed")
                    # don't say WHICH process — fold the pid in when present.
                    if event in ("allocated", "retry_allocated") and pid:
                        size = entry.get("size")
                        prefix = "Retry allocated" if event == "retry_allocated" else "Allocated"
                        event_label = f"{prefix} {pid} ({size}K)" if size is not None else f"{prefix} {pid}"
                    elif event == "allocation_failed" and pid:
                        event_label = f"Failed: {pid}"
                    elif event == "removed" and pid:
                        event_label = f"Removed {pid}"
                    elif event == "compacted":
                        event_label = "Compacted"
                    elif event == "completed":
                        event_label = "Completed"
                    else:
                        event_label = event or "—"

                    label = f"{snap_idx+1}: {event_label}"

                    for block in memory_map:
                        pid_key = "FREE" if block.get("free", True) else block["pid"]
                        size = block["end"] - block["start"]
                        base = block["start"]

                        if pid_key not in traces:
                            traces[pid_key] = {
                                "x": [],
                                "y": [],
                                "base": [],
                                "text": [],
                                "color": "#2a2d3e" if pid_key == "FREE" else pid_colors.get(pid_key, "#888"),
                            }

                        traces[pid_key]["x"].append(label)
                        traces[pid_key]["y"].append(size)
                        traces[pid_key]["base"].append(base)
                        traces[pid_key]["text"].append(f"{pid_key}<br>{base}–{block['end']}")

                fig = go.Figure()

                # Add FREE first (renders at bottom of legend)
                if "FREE" in traces:
                    t = traces["FREE"]
                    fig.add_trace(go.Bar(
                        name="FREE",
                        x=t["x"],
                        y=t["y"],
                        base=t["base"],
                        text=t["text"],
                        textposition="inside",
                        marker_color=t["color"],
                        marker_line=dict(color="#0f1117", width=1),
                        hoverinfo="text",
                        insidetextanchor="middle",
                    ))

                # Add process blocks
                for pid_key, t in traces.items():
                    if pid_key == "FREE":
                        continue
                    fig.add_trace(go.Bar(
                        name=pid_key,
                        x=t["x"],
                        y=t["y"],
                        base=t["base"],
                        text=t["text"],
                        textposition="inside",
                        marker_color=t["color"],
                        marker_line=dict(color="#0f1117", width=1),
                        hoverinfo="text",
                        insidetextanchor="middle",
                    ))

                fig.update_layout(
                    barmode="overlay",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(
                        title="Snapshot (Event)",
                        gridcolor="#2a2d3e",
                        tickangle=-30,
                    ),
                    yaxis=dict(
                        title="Memory Address (K)",
                        gridcolor="#2a2d3e",
                        range=[0, total_mem],
                    ),
                    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2a2d3e"),
                    margin=dict(l=40, r=20, t=20, b=80),
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No memory map data available.")

        with tab_timeline:
            timeline = mem_result.get("timeline", [])
            if timeline:
                st.dataframe(timeline, use_container_width=True, hide_index=True)
            else:
                st.info("No timeline data available.")

        with tab_raw:
            st.json(mem_result)

# -------------------------------------------------------------
# PAGE: VIRTUAL MEMORY
# -------------------------------------------------------------
elif page == "Virtual Memory":
    st.title("Virtual Memory")
    st.caption("Module 6 — Page Replacement Algorithms")
    st.divider()

    # Sidebar inputs
    st.sidebar.subheader("Page Replacement Parameters")

    VM_ALGORITHMS = ["FIFO", "LRU", "LRU Approximation", "Optimal", "LFU", "MFU"]
    vm_algorithm = st.sidebar.selectbox(
        "Algorithm",
        VM_ALGORITHMS,
        index=VM_ALGORITHMS.index(st.session_state.sticky_vm_algorithm),
        key="vm_algorithm_select",
        help="Select the page replacement algorithm."
    )

    if vm_algorithm != st.session_state.sticky_vm_algorithm:
        st.session_state.vm_response = None

    st.session_state.sticky_vm_algorithm = vm_algorithm

    vm_frames = st.sidebar.number_input(
        "Number of Frames",
        min_value=1, step=1, value=1,
        key="vm_frames_input",
        help="Number of frames available in physical memory."
    )

    st.sidebar.divider()
    st.sidebar.caption("Enter page reference string separated by commas.")
    vm_pages_input = st.sidebar.text_input(
        "Page Reference String",
        placeholder="e.g. 7, 0, 1, 2, 0, 3",
        label_visibility="collapsed",
        key="vm_pages_input"
    )

    try:
        vm_pages_list = [int(p.strip()) for p in vm_pages_input.split(",") if p.strip()]
    except ValueError:
        st.sidebar.error("Invalid input — enter comma-separated integers only.")
        vm_pages_list = []

    st.sidebar.divider()
    vm_run_clicked = st.sidebar.button(
        f"▶ Run {vm_algorithm}",
        use_container_width=True,
        type="primary",
        disabled=len(vm_pages_list) == 0,
        key="vm_run_btn"
    )

    # VM algorithm to endpoint mapping — now using the real named constants
    # from config.py (added by the architect) instead of hand-built f-strings.
    VM_ALGORITHM_MAP = {
        "FIFO": VM_FIFO_API,
        "LRU": VM_LRU_API,
        "LRU Approximation": VM_LRU_APPROX_API,
        "Optimal": VM_OPTIMAL_API,
        "LFU": VM_LFU_API,
        "MFU": VM_MFU_API,
    }

    # Main area
    st.subheader(f"Algorithm: {vm_algorithm}")

    if vm_run_clicked:
        vm_payload = {
            "pages": vm_pages_list,
            "frames": int(vm_frames),
        }

        with st.status(f"Running {vm_algorithm}...", expanded=True) as status:
            try:
                st.write("Sending request to API...")
                response = requests.post(
                    VM_ALGORITHM_MAP[vm_algorithm],
                    json=vm_payload,
                    timeout=10,
                )
                response.raise_for_status()
                st.session_state.vm_response = response.json()
                st.write("Response received.")
                status.update(label="Simulation complete!", state="complete", expanded=False)
                st.toast("Simulation complete!", icon="✅")

            except requests.exceptions.Timeout:
                status.update(label="Request timed out.", state="error", expanded=False)
                st.error("Request timed out. Is the backend running?")
                st.session_state.vm_response = None

            except requests.exceptions.HTTPError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                status.update(label="API error.", state="error", expanded=False)
                st.error(f"API error: {detail}")
                st.session_state.vm_response = None

            except requests.exceptions.ConnectionError:
                status.update(label="Cannot connect to API.", state="error", expanded=False)
                st.error("Cannot connect to the API. Is the backend running?")
                st.session_state.vm_response = None

    if st.session_state.vm_response is not None:
        st.divider()
        vm_result = st.session_state.vm_response

        tab_summary, tab_timeline, tab_raw = st.tabs(["Summary", "Page Timeline", "Raw Response"])

        with tab_summary:
            c1, c2 = st.columns(2)
            with c1:
                st.metric(
                    "Page Fault Count",
                    f"{vm_result.get('page_fault_count', 0)}",
                    help="Total number of page faults that occurred."
                )
            with c2:
                st.metric(
                    "Page Fault Rate",
                    f"{vm_result.get('page_fault_rate', 0):.2f}",
                    help="Ratio of page faults to total page references."
                )

            st.divider()

            # Page fault visualization — textbook-style stacked frame columns
            # (matches the standard OS textbook diagram: one column per
            # reference, each column shows the full set of pages currently
            # resident in memory at that step, color-coded red on a fault).
            #
            # IMPORTANT DESIGN NOTE: frames_state's list order does NOT
            # reliably convey recency/age — FIFO (and others) replace a
            # victim IN PLACE at its old list index, so position-in-list is
            # an implementation artifact, not a meaningful "how old is this
            # page" signal. Sorting numerically per column gives a stable,
            # honest layout instead of implying an age story the data
            # doesn't actually support.
            #
            # For LFU / MFU / LRU Approximation, the backend's "frequencies"
            # field carries real diagnostic value (true use-counts for LFU/
            # MFU, reference bits — 0 or 1 — for LRU Approximation's
            # second-chance algorithm) and is folded into the hover text
            # when present. FIFO/LRU/Optimal always send frequencies=None,
            # so they just show the page number with no extra annotation.
            st.subheader("Page Fault Timeline")
            timeline = vm_result.get("timeline", [])
            if timeline:
                import plotly.graph_objects as go

                num_frames = vm_result.get("frames", max((len(t.get("frames_state", [])) for t in timeline), default=1))
                fault_color = "#ef4444"
                hit_color = "#00ff9d"
                empty_color = "#2a2d3e"

                fig = go.Figure()
                # One trace PER ROW (frame slot), built column by column, so
                # each column's frame contents stack from row 0 (bottom) to
                # row num_frames-1 (top) — matching the textbook's vertical
                # frame-box layout.
                row_traces = [{"x": [], "y": [], "base": [], "text": [], "color": [], "customdata": []} for _ in range(num_frames)]

                for ref_idx, t in enumerate(timeline):
                    page = t.get("page")
                    fault = t.get("fault", False)
                    frames_state = sorted(t.get("frames_state", []) or [])
                    freqs = t.get("frequencies")
                    label = str(ref_idx + 1)
                    bar_color = fault_color if fault else hit_color

                    for row in range(num_frames):
                        trace = row_traces[row]
                        trace["x"].append(label)
                        trace["base"].append(row)
                        trace["y"].append(1)
                        if row < len(frames_state):
                            p = frames_state[row]
                            # NOTE: after a real HTTP round-trip, JSON object
                            # keys are always strings — frequencies (a dict)
                            # will have string keys ("7") even though
                            # frames_state (a plain list) keeps its int
                            # values (7). A direct `p in freqs` lookup with
                            # an int p against string keys silently fails
                            # every time, dropping all hover annotations with
                            # no error. Look up by str(p) instead.
                            freq_val = freqs.get(str(p)) if freqs is not None else None
                            if freq_val is not None:
                                hover = f"Page {p} (ref bit/freq: {freq_val})"
                            else:
                                hover = f"Page {p}"
                            trace["text"].append(str(p))
                            trace["color"].append(bar_color)
                            trace["customdata"].append(hover)
                        else:
                            # Frame slot not yet filled (early references before
                            # all frames are occupied for the first time).
                            trace["text"].append("")
                            trace["color"].append(empty_color)
                            trace["customdata"].append("empty")

                for row in range(num_frames):
                    trace = row_traces[row]
                    fig.add_trace(go.Bar(
                        x=trace["x"],
                        y=trace["y"],
                        base=trace["base"],
                        text=trace["text"],
                        textposition="inside",
                        marker_color=trace["color"],
                        marker_line=dict(color="#0f1117", width=1),
                        customdata=trace["customdata"],
                        hovertemplate="%{customdata}<extra></extra>",
                        insidetextanchor="middle",
                        showlegend=False,
                    ))

                fig.update_layout(
                    barmode="stack",
                    xaxis_title="Reference",
                    yaxis=dict(visible=False, range=[0, num_frames]),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(gridcolor="#2a2d3e"),
                    showlegend=False,
                    margin=dict(l=20, r=20, t=20, b=40),
                    height=max(180, 60 * num_frames),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("🔴 Red column = Page Fault  |  🟢 Green column = Page Hit  |  Rows sorted numerically — list position in the raw data doesn't represent recency/age.")

        with tab_timeline:
            timeline = vm_result.get("timeline", [])
            if timeline:
                st.dataframe(timeline, use_container_width=True, hide_index=True)
            else:
                st.info("No timeline data available.")

        with tab_raw:
            st.json(vm_result)

# -------------------------------------------------------------
# PAGE: COMPARE
# -------------------------------------------------------------
elif page == "Compare":
    st.title("Compare Mode")
    st.caption("Compare all algorithms on the same input side by side.")
    st.divider()

    section = st.radio(
        "Compare Type",
        ["CPU Scheduling", "Disk Scheduling"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.divider()

    if section == "CPU Scheduling":
        st.subheader("CPU Scheduling — Algorithm Comparison")
        st.caption("Runs all CPU scheduling algorithms on the same process list.")

        # Hierarchy rule (informational only — does NOT gate the button):
        # - Whether the process list carries a "priority" field is what actually
        #   determines whether Priority algorithms can be included in the backend's
        #   comparison. This is driven by the data itself, not by which algorithm
        #   label was last selected, so it's correct no matter how the user got here.
        # - The compare button should ALWAYS be enabled once processes exist —
        #   /schedule/analyze runs whatever it can and simply skips/handles the
        #   algorithms that don't apply. The warning below is just a heads-up,
        #   not a hard gate.
        has_processes = len(st.session_state.processes) > 0
        has_priority_data = any("priority" in p for p in st.session_state.processes)

        if st.session_state.last_algorithm:
            st.caption(f"Currently selected on Scheduler page: **{st.session_state.last_algorithm}**")

        if has_processes:
            st.markdown(f"**Processes from Scheduler page:** {len(st.session_state.processes)}")
            for p in st.session_state.processes:
                if "priority" in p:
                    st.text(f"{p['pid']}  |  Arrival: {p['arrival_time']}  |  Burst: {p['burst_time']}  |  Priority: {p['priority']}")
                else:
                    st.text(f"{p['pid']}  |  Arrival: {p['arrival_time']}  |  Burst: {p['burst_time']}")

            if not has_priority_data:
                st.warning(
                    "Your process list doesn't have priority values yet, so Priority algorithms "
                    "will be excluded from this comparison (Round Robin and the rest will still run). "
                    "To include Priority algorithms, add processes with priority on the Scheduler page first."
                )
        else:
            st.info("No processes added yet. Go to the Scheduler page to add processes first.")

        st.divider()

        cpu_compare_disabled = not has_processes

        if st.button("▶ Run CPU Compare", type="primary", disabled=cpu_compare_disabled, key="cpu_compare_btn"):
            with st.status("Running CPU comparison...", expanded=True) as status:
                try:
                    st.write("Sending request to /schedule/analyze...")
                    response = requests.post(
                        SCHEDULE_ANALYZE_API,
                        json={"processes": st.session_state.processes},
                        timeout=10,
                    )
                    response.raise_for_status()
                    st.session_state.compare_results = response.json()
                    status.update(label="Comparison complete!", state="complete", expanded=False)
                    st.toast("CPU comparison complete!", icon="✅")

                except requests.exceptions.Timeout:
                    status.update(label="Request timed out.", state="error", expanded=False)
                    st.error("Request timed out. Is the backend running?")
                    st.session_state.compare_results = None

                except requests.exceptions.HTTPError as e:
                    try:
                        detail = e.response.json().get("detail", str(e))
                    except Exception:
                        detail = str(e)
                    status.update(label="API error.", state="error", expanded=False)
                    st.error(f"API error: {detail}")
                    st.session_state.compare_results = None

                except requests.exceptions.ConnectionError:
                    status.update(label="Cannot connect to API.", state="error", expanded=False)
                    st.error("Cannot connect to the API. Is the backend running?")
                    st.session_state.compare_results = None

        if st.session_state.compare_results is not None:
            import plotly.graph_objects as go

            results = st.session_state.compare_results.get("results", {})
            algo_names = list(results.keys())

            avg_waiting    = [results[a].get("avg_waiting_time", 0) for a in algo_names]
            avg_turnaround = [results[a].get("avg_turnaround_time", 0) for a in algo_names]
            cpu_util       = [results[a].get("cpu_utilization", 0) for a in algo_names]

            tab_chart, tab_table, tab_raw = st.tabs(["Chart", "Table", "Raw Response"])

            with tab_chart:
                st.subheader("Algorithm Comparison")
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Avg Waiting Time", x=algo_names, y=avg_waiting, marker_color="#00ff9d"))
                fig.add_trace(go.Bar(name="Avg Turnaround Time", x=algo_names, y=avg_turnaround, marker_color="#3b82f6"))
                fig.add_trace(go.Bar(name="CPU Utilization (%)", x=algo_names, y=cpu_util, marker_color="#f59e0b"))
                fig.update_layout(
                    barmode="group",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(gridcolor="#2a2d3e"),
                    yaxis=dict(gridcolor="#2a2d3e", title="Value"),
                    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2a2d3e"),
                    margin=dict(l=40, r=20, t=20, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab_table:
                table_data = []
                for a in algo_names:
                    table_data.append({
                        "Algorithm": a.upper(),
                        "Avg Waiting Time": round(results[a].get("avg_waiting_time", 0), 2),
                        "Avg Turnaround Time": round(results[a].get("avg_turnaround_time", 0), 2),
                        "CPU Utilization (%)": round(results[a].get("cpu_utilization", 0), 2),
                    })
                st.dataframe(table_data, use_container_width=True, hide_index=True)

            with tab_raw:
                st.json(results)

        else:
            st.info("Run a comparison above to see CPU scheduling results here.")

    elif section == "Disk Scheduling":
        st.subheader("Disk Scheduling — Algorithm Comparison")
        st.caption("Runs all disk scheduling algorithms on the same input. Key metric: total head movement.")

        st.divider()

        if st.session_state.disk_params_set:
            params = st.session_state.disk_params
            st.markdown("**Parameters from Mass Storage page:**")
            st.text(f"Initial Head Position: {params['head']}")
            st.text(f"Number of Tracks: {params['number_of_tracks']}")
            st.text(f"Cylinder Requests: {params['requests_input']}")

            # Direction handling:
            # Whether direction should be an editable input or a read-only display
            # depends on the algorithm CURRENTLY SELECTED on the Mass Storage page
            # (sticky_disk_algorithm) — not on whichever algorithm was last actually
            # run (last_disk_algorithm). Those are different things: a user can
            # switch the Mass Storage dropdown to SCAN without clicking Run again,
            # and this page should reflect that immediately. FCFS/SSTF never have
            # a direction concept at all, so they always get the editable input.
            no_direction_algos = ["FCFS", "SSTF"]
            current_disk_algorithm = st.session_state.sticky_disk_algorithm
            if current_disk_algorithm in no_direction_algos:
                st.caption(f"{current_disk_algorithm} doesn't use direction. Select one below to include SCAN/C-SCAN/LOOK/C-LOOK in the comparison.")
                cmp_direction = st.selectbox(
                    "Direction for comparison",
                    ["right", "left"],
                    key="cmp_direction_extra"
                )
            else:
                cmp_direction = params["direction"]
                st.text(f"Direction: {cmp_direction}")

            try:
                cmp_requests_list = [int(r.strip()) for r in params["requests_input"].split(",") if r.strip()]
            except ValueError:
                st.error("Invalid request data from Mass Storage page.")
                cmp_requests_list = []
        else:
            st.info("No parameters set yet. Go to the Mass Storage page first.")
            cmp_requests_list = []
            cmp_direction = "right"

        st.divider()

        if st.button("▶ Run Disk Compare", type="primary", disabled=len(cmp_requests_list) == 0, key="disk_compare_btn"):
            disk_payload = {
                "head": int(st.session_state.disk_params["head"]),
                "requests": cmp_requests_list,
                "number_of_tracks": int(st.session_state.disk_params["number_of_tracks"]),
                "direction": cmp_direction,
            }

            with st.status("Running disk comparison...", expanded=True) as status:
                try:
                    st.write("Sending request to /disk/analyze...")
                    response = requests.post(DISK_ANALYZE_API, json=disk_payload, timeout=10)
                    response.raise_for_status()
                    st.session_state.disk_compare_results = response.json()
                    status.update(label="Disk comparison complete!", state="complete", expanded=False)
                    st.toast("Disk comparison complete!", icon="✅")

                except requests.exceptions.Timeout:
                    status.update(label="Request timed out.", state="error", expanded=False)
                    st.error("Request timed out. Is the backend running?")
                    st.session_state.disk_compare_results = None

                except requests.exceptions.HTTPError as e:
                    try:
                        detail = e.response.json().get("detail", str(e))
                    except Exception:
                        detail = str(e)
                    status.update(label="API error.", state="error", expanded=False)
                    st.error(f"API error: {detail}")
                    st.session_state.disk_compare_results = None

                except requests.exceptions.ConnectionError:
                    status.update(label="Cannot connect to API.", state="error", expanded=False)
                    st.error("Cannot connect to the API. Is the backend running?")
                    st.session_state.disk_compare_results = None

        if st.session_state.disk_compare_results is not None:
            import plotly.graph_objects as go

            disk_results = st.session_state.disk_compare_results.get("results", {})
            disk_algo_names = list(disk_results.keys())
            total_movements = [disk_results[a].get("total_head_movement", 0) for a in disk_algo_names]

            tab_chart, tab_table, tab_raw = st.tabs(["Chart", "Table", "Raw Response"])

            with tab_chart:
                st.subheader("Total Head Movement Comparison")
                st.caption("Lower total head movement = more efficient algorithm.")
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=disk_algo_names,
                    y=total_movements,
                    marker_color="#3b82f6",
                    text=total_movements,
                    textposition="outside",
                ))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(gridcolor="#2a2d3e"),
                    yaxis=dict(gridcolor="#2a2d3e", title="Total Head Movement"),
                    showlegend=False,
                    margin=dict(l=40, r=20, t=40, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab_table:
                disk_table_data = []
                for a in disk_algo_names:
                    disk_table_data.append({
                        "Algorithm": a.upper(),
                        "Total Head Movement": disk_results[a].get("total_head_movement", 0),
                    })
                disk_table_data.sort(key=lambda x: x["Total Head Movement"])
                st.dataframe(disk_table_data, use_container_width=True, hide_index=True)

            with tab_raw:
                st.json(disk_results)

        else:
            st.info("Run a comparison above to see disk scheduling results here.")

# -------------------------------------------------------------
# PAGE: RECOMMEND
# -------------------------------------------------------------
elif page == "Recommend":
    st.title("Recommendation")
    st.caption("Get an algorithm recommendation based on your process set.")
    st.divider()
    st.info("Coming soon - waiting for Backend Architect to deliver /recommend endpoint (Week 3).")
    # response = requests.post(f"{API_BASE}/recommend", json={"processes": st.session_state.processes})
    # result = response.json()
    # st.write(f"Best Algorithm: {result['best_algorithm']}")
    # st.write(f"Reason: {result['reason']}")