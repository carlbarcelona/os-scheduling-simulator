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

if "last_response" not in st.session_state:
    st.session_state.last_response = None

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

# -- SIDEBAR NAVIGATION
st.sidebar.title("⚙️ OS Scheduling Simulator")
st.sidebar.caption("OS Scheduling Algorithm Visualizer")
page = st.sidebar.radio(
    "Navigate",
    ["Scheduler", "Mass Storage", "Memory", "Virtual Memory", "Compare", "Recommend", "Deadlock"],
    label_visibility="collapsed"
)

st.sidebar.divider()

# -------------------------------------------------------------
# PAGE: SCHEDULER
# -------------------------------------------------------------
if page == "Scheduler":

    algorithm = st.sidebar.selectbox(
        "Algorithm",
        ["FCFS", "SJF Non-Preemptive", "SJF Preemptive", "Round Robin", "Priority Non-Preemptive", "Priority Preemptive"],
        help="Select the CPU scheduling algorithm to simulate."
    )

    quantum = None
    if algorithm == "Round Robin":
        quantum = st.sidebar.number_input(
            "Quantum",
            min_value=1, step=1, value=2,
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
            st.plotly_chart(render_gantt(result["timeline"], result["schedule"]), use_container_width=True)

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

    disk_algorithm = st.sidebar.selectbox(
        "Algorithm",
        ["FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"],
        help="Select the disk scheduling algorithm."
    )

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
            # The backend marks the C-SCAN / C-LOOK boundary jump explicitly as "?"
            # inside the sequence array — we detect that literal marker (not inferred
            # from distance) and render the jump segment as dashed, matching the
            # textbook diagram convention. Numeric segments stay solid.
            st.subheader("Seek Pattern")
            sequence = disk_result.get("sequence", [])
            if sequence:
                import plotly.graph_objects as go

                # Find index of the literal "?" marker, if present
                marker_idx = None
                for i, val in enumerate(sequence):
                    if val == "?":
                        marker_idx = i
                        break

                if marker_idx is not None:
                    # Points before the marker, and points after — "?" itself is not plotted
                    before = [(v, s) for s, v in enumerate(sequence) if s < marker_idx]
                    after = [(v, s) for s, v in enumerate(sequence) if s > marker_idx]

                    fig = go.Figure()

                    # Solid segment before the boundary jump
                    if before:
                        fig.add_trace(go.Scatter(
                            x=[p[0] for p in before],
                            y=[p[1] for p in before],
                            mode="lines+markers",
                            line=dict(color="#00ff9d", width=2),
                            marker=dict(size=8, color="#00ff9d", symbol="circle"),
                            showlegend=False,
                        ))

                    # Dashed connector spanning the "?" boundary touch —
                    # connects last point before the marker to first point after it
                    if before and after:
                        fig.add_trace(go.Scatter(
                            x=[before[-1][0], after[0][0]],
                            y=[before[-1][1], after[0][1]],
                            mode="lines",
                            line=dict(color="#00ff9d", width=2, dash="dash"),
                            showlegend=False,
                        ))

                    # Solid segment after the boundary jump
                    if after:
                        fig.add_trace(go.Scatter(
                            x=[p[0] for p in after],
                            y=[p[1] for p in after],
                            mode="lines+markers",
                            line=dict(color="#00ff9d", width=2),
                            marker=dict(size=8, color="#00ff9d", symbol="circle"),
                            showlegend=False,
                        ))
                else:
                    # FCFS, SSTF, SCAN, LOOK — no "?" marker, single continuous solid path
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(sequence),
                        y=list(range(len(sequence))),
                        mode="lines+markers",
                        line=dict(color="#00ff9d", width=2),
                        marker=dict(size=8, color="#00ff9d", symbol="circle"),
                        showlegend=False,
                    ))

                fig.update_layout(
                    xaxis_title="Cylinder Position",
                    yaxis_title="Step",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(gridcolor="#2a2d3e", range=[0, number_of_tracks]),
                    yaxis=dict(gridcolor="#2a2d3e", autorange="reversed"),
                    showlegend=False,
                    margin=dict(l=40, r=20, t=20, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)
                if marker_idx is not None:
                    st.caption("Dashed segment = head jump-back at boundary (no service), solid = servicing requests.")

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
        help="Total memory capacity in kilobytes."
    )

    fit_strategy = st.sidebar.selectbox(
        "Fit Strategy",
        ["first", "best", "worst", "next"],
        help="Memory allocation strategy. First Fit, Best Fit, Worst Fit, or Next Fit."
    )

    compaction = st.sidebar.selectbox(
        "Compaction",
        ["With Compaction", "Without Compaction"],
        help="Whether to compact memory when allocation fails."
    )

    st.sidebar.divider()
    st.sidebar.subheader("Add Process")

    col_mpid, col_msize = st.sidebar.columns(2)
    with col_mpid:
        m_pid = st.text_input("Process ID", placeholder="e.g. P1", key="m_pid_input")
    with col_msize:
        m_size = st.number_input("Size (K)", min_value=1, step=1, value=1, key="m_size_input")

    m_burst = st.sidebar.number_input(
        "Burst Time",
        min_value=0.1, step=0.5, value=0.1,
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
        # NOTE: MVT endpoints not yet in config.py — pending Architect.
        # Endpoint will be either /memory/mvt_with_compaction or /memory/mvt_without_compaction
        mem_payload = {
            "total_memory": int(total_memory),
            "fit_strategy": fit_strategy,
            "processes": st.session_state.memory_processes,
        }

        # Placeholder endpoint — update when Architect adds to config.py
        mem_endpoint = f"{API_BASE}/memory/mvt_with_compaction" if compaction == "With Compaction" else f"{API_BASE}/memory/mvt_without_compaction"

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
                st.error("Cannot connect to the API. Is the backend running? (Memory endpoints pending from Backend Architect)")
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
                    label = f"{snap_idx+1}: {event}"

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

    vm_algorithm = st.sidebar.selectbox(
        "Algorithm",
        ["FIFO", "LRU", "LRU Approximation", "Optimal", "LFU", "MFU"],
        help="Select the page replacement algorithm."
    )

    vm_frames = st.sidebar.number_input(
        "Number of Frames",
        min_value=1, step=1, value=1,
        help="Number of frames available in physical memory."
    )

    st.sidebar.divider()
    st.sidebar.caption("Enter page reference string separated by commas.")
    vm_pages_input = st.sidebar.text_input(
        "Page Reference String",
        value="",
        placeholder="e.g. 7, 0, 1, 2, 0, 3",
        label_visibility="collapsed"
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

    # VM algorithm to endpoint mapping
    # NOTE: VM endpoints not yet in config.py — pending Architect.
    VM_ALGORITHM_MAP = {
        "FIFO": f"{API_BASE}/vm/fifo",
        "LRU": f"{API_BASE}/vm/lru",
        "LRU Approximation": f"{API_BASE}/vm/lru_approx",
        "Optimal": f"{API_BASE}/vm/optimal",
        "LFU": f"{API_BASE}/vm/lfu",
        "MFU": f"{API_BASE}/vm/mfu",
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
                st.error("Cannot connect to the API. Is the backend running? (Virtual Memory endpoints pending from Backend Architect)")
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

            # Page fault visualization — Plotly bar chart
            st.subheader("Page Fault Timeline")
            timeline = vm_result.get("timeline", [])
            if timeline:
                import plotly.graph_objects as go
                pages_seq = [str(t["page"]) for t in timeline]
                faults = [1 if t["fault"] else 0 for t in timeline]
                colors = ["#ef4444" if f else "#00ff9d" for f in faults]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=list(range(len(pages_seq))),
                    y=[1] * len(pages_seq),
                    marker_color=colors,
                    text=pages_seq,
                    textposition="inside",
                    hovertext=[f"Page {p}: {'FAULT' if f else 'HIT'}" for p, f in zip(pages_seq, faults)],
                    hoverinfo="text",
                ))
                fig.update_layout(
                    xaxis_title="Reference",
                    yaxis=dict(visible=False),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                    xaxis=dict(gridcolor="#2a2d3e"),
                    showlegend=False,
                    margin=dict(l=20, r=20, t=20, b=40),
                    height=120,
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("🔴 Red = Page Fault  |  🟢 Green = Page Hit")

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
        st.caption("Runs all CPU scheduling algorithms on the same process list. Priority and Quantum values, if present, are ignored by algorithms that don't use them.")

        if st.session_state.processes:
            st.markdown(f"**Processes from Scheduler page:** {len(st.session_state.processes)}")
            for p in st.session_state.processes:
                if "priority" in p:
                    st.text(f"{p['pid']}  |  Arrival: {p['arrival_time']}  |  Burst: {p['burst_time']}  |  Priority: {p['priority']}")
                else:
                    st.text(f"{p['pid']}  |  Arrival: {p['arrival_time']}  |  Burst: {p['burst_time']}")
        else:
            st.info("No processes added yet. Go to the Scheduler page to add processes first.")

        st.divider()

        if st.button("▶ Run CPU Compare", type="primary", disabled=len(st.session_state.processes) == 0, key="cpu_compare_btn"):
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
                    st.error("Cannot connect to the API. Is the backend running? (/schedule/analyze endpoint pending from Backend Architect)")
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
            st.info("CPU comparison results will display here once /schedule/analyze is available from Backend Architect.")

    elif section == "Disk Scheduling":
        st.subheader("Disk Scheduling — Algorithm Comparison")
        st.caption("Runs all disk scheduling algorithms on the same input. Key metric: total head movement.")

        st.divider()

        if st.session_state.disk_params_set:
            params = st.session_state.disk_params
            st.markdown("**Parameters from Mass Storage page:**")
            st.text(f"Initial Head Position: {params['head']}")
            st.text(f"Number of Tracks: {params['number_of_tracks']}")
            st.text(f"Direction: {params['direction']}")
            st.text(f"Cylinder Requests: {params['requests_input']}")

            try:
                cmp_requests_list = [int(r.strip()) for r in params["requests_input"].split(",") if r.strip()]
            except ValueError:
                st.error("Invalid request data from Mass Storage page.")
                cmp_requests_list = []
        else:
            st.info("No parameters set yet. Go to the Mass Storage page first to set head position, tracks, direction, and requests.")
            cmp_requests_list = []

        st.divider()

        if st.button("▶ Run Disk Compare", type="primary", disabled=len(cmp_requests_list) == 0, key="disk_compare_btn"):
            disk_payload = {
                "head": int(st.session_state.disk_params["head"]),
                "requests": cmp_requests_list,
                "number_of_tracks": int(st.session_state.disk_params["number_of_tracks"]),
                "direction": st.session_state.disk_params["direction"],
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
                    st.error("Cannot connect to the API. Is the backend running? (/disk/analyze endpoint pending from Backend Architect)")
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
            st.info("Disk comparison results will display here once /disk/analyze is available from Backend Architect.")

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

# -------------------------------------------------------------
# PAGE: DEADLOCK
# -------------------------------------------------------------
elif page == "Deadlock":
    st.title("Deadlock Detection")
    st.caption("Banker's Algorithm — resource allocation and deadlock detection.")
    st.divider()
    st.info("Pending scope confirmation - Banker's Algorithm UI placeholder (Week 3).")
    # from components.rag import render_rag
    # st.plotly_chart(render_rag(allocation, max_matrix, available))