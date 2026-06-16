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

# -- ANALYZE_API (not yet in config.py - flagged to Architect for addition)
ANALYZE_API = f"{API_BASE}/analyze"

# -- Session state initialization
if "processes" not in st.session_state:
    st.session_state.processes = []

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "compare_results" not in st.session_state:
    st.session_state.compare_results = None

# -- SIDEBAR NAVIGATION
st.sidebar.title("⚙️ OS Scheduling Simulator")
st.sidebar.caption("OS Scheduling Algorithm Visualizer")
page = st.sidebar.radio(
    "Navigate",
    ["Scheduler", "Memory", "Compare", "Recommend", "Deadlock"],
    label_visibility="collapsed"
)

st.sidebar.divider()

# -------------------------------------------------------------
# PAGE: SCHEDULER
# -------------------------------------------------------------
if page == "Scheduler":

    # Algorithm selector
    algorithm = st.sidebar.selectbox(
        "Algorithm",
        ["FCFS", "SJF Non-Preemptive", "SJF Preemptive", "Round Robin", "Priority Non-Preemptive", "Priority Preemptive"],
        help="Select the CPU scheduling algorithm to simulate."
    )

    # Quantum input (only for Round Robin)
    quantum = None
    if algorithm == "Round Robin":
        quantum = st.sidebar.number_input(
            "Quantum",
            min_value=1, step=1, value=2,
            help="Time slice allocated to each process in Round Robin."
        )

    st.sidebar.divider()

    # Add process form
    st.sidebar.subheader("Add Process")

    col_pid, col_at = st.sidebar.columns(2)
    with col_pid:
        pid = st.text_input("Process ID", placeholder="e.g. P1", label_visibility="visible", key="pid_input")
    with col_at:
        arrival_time = st.number_input("Arrival", min_value=0, step=1, key="arrival_input")

    col_bt, col_pr = st.sidebar.columns(2)
    with col_bt:
        burst_time = st.number_input("Burst", min_value=1, step=1, key="burst_input")

    # Priority input (only for Priority algorithms)
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

    # Process list in sidebar
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

    # -- MAIN AREA
    st.title("CPU Scheduler")
    st.caption(f"Algorithm: **{algorithm}** · Processes: **{len(st.session_state.processes)}**")

    st.divider()

    # Algorithm to endpoint mapping
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

    # Current process table + Run button
    col_table, col_run = st.columns([3, 1])

    with col_table:
        if st.session_state.processes:
            st.dataframe(
                st.session_state.processes,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No processes added yet. Use the sidebar to add processes.")

    with col_run:
        st.write("")
        run_clicked = st.button(
            f"▶ Run {algorithm}",
            use_container_width=True,
            type="primary",
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

    # Results
    if st.session_state.last_response is not None:
        st.divider()

        result = st.session_state.last_response

        # Tabs for results sections
        tab_metrics, tab_gantt, tab_raw = st.tabs(["Metrics", "Gantt Chart", "Raw Response"])

        with tab_metrics:
            # Metrics row with tooltips (Week 3)
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
# PAGE: MEMORY
# -------------------------------------------------------------
elif page == "Memory":
    st.title("Memory Visualizer")
    st.caption("Module 5 — Memory Management")
    st.divider()
    st.info("Coming soon - waiting for Visualizer to deliver components/memory.py and Algorithm Engineer to deliver memory management algorithms (Module 5).")
    # from components.memory import render_memory
    # st.plotly_chart(render_memory(blocks, algorithm))

# -------------------------------------------------------------
# PAGE: COMPARE
# -------------------------------------------------------------
elif page == "Compare":
    st.title("Compare Mode")
    st.caption("Run all algorithms on the same process list and compare results side by side.")
    st.divider()

    if st.session_state.processes:
        st.dataframe(st.session_state.processes, use_container_width=True, hide_index=True)
    else:
        st.info("No processes added yet. Go to Scheduler page to add processes.")

    st.divider()

    if st.button("▶ Run Compare Mode", type="primary", disabled=len(st.session_state.processes) == 0):
        with st.status("Running comparison...", expanded=True) as status:
            try:
                st.write("Sending request to /analyze...")
                response = requests.post(
                    ANALYZE_API,
                    json={"processes": st.session_state.processes},
                    timeout=10,
                )
                response.raise_for_status()
                st.session_state.compare_results = response.json()
                status.update(label="Comparison complete!", state="complete", expanded=False)
                st.toast("Comparison complete!", icon="✅")

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
                st.error("Cannot connect to the API. Is the backend running? (/analyze endpoint pending from Backend Architect)")
                st.session_state.compare_results = None

    if st.session_state.compare_results is not None:
        results = st.session_state.compare_results.get("results", {})
        cols = st.columns(4)
        algo_names = list(results.keys())[:4]
        for col, name in zip(cols, algo_names):
            with col:
                st.markdown(f"**{name.upper()}**")
                st.json(results[name])
    else:
        st.info("Compare Mode results will display here as 4 columns once /analyze is available from Backend Architect.")

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