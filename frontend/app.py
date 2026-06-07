# frontend/app.py
import streamlit as st
import requests
from config import *

# ── Session state initialization ─────────────────────────────────────────────
if "processes" not in st.session_state:
    st.session_state.processes = []

if "last_response" not in st.session_state:
    st.session_state.last_response = None

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.title("CPU Scheduling Simulator")

# -- Algorithm selector
algorithm = st.sidebar.selectbox(
    "Algorithm",
    ["FCFS", "SJF Non-Preemptive", "SJF Preemptive", "Round Robin", "Priority Non-Preemptive", "Priority Preemptive"]
)

# -- Quantum input (only for Round Robin)
quantum = None
if algorithm == "Round Robin":
    quantum = st.sidebar.number_input("Quantum", min_value=1, step=1, value=2)

st.sidebar.markdown("---")

# -- Add process form
st.sidebar.subheader("Add Process")
pid = st.sidebar.text_input("Process ID")
arrival_time = st.sidebar.number_input("Arrival Time", min_value=0, step=1)
burst_time = st.sidebar.number_input("Burst Time", min_value=1, step=1)

if st.sidebar.button("Add Process"):
    st.session_state.processes.append({
        "pid": pid,
        "arrival_time": int(arrival_time),
        "burst_time": int(burst_time),
    })
    st.rerun()

st.sidebar.markdown("---")

# -- Process list in sidebar
if st.session_state.processes:
    st.sidebar.subheader(f"Process Queue — {len(st.session_state.processes)} Processes")
    for p in st.session_state.processes:
        st.sidebar.write(f"**{p['pid']}** | Arrival: {p['arrival_time']} | Burst: {p['burst_time']}")

if st.sidebar.button("Clear All Processes"):
    st.session_state.processes = []
    st.session_state.last_response = None
    st.rerun()

# ── MAIN AREA ─────────────────────────────────────────────────────────────────
st.title("CPU Scheduling Simulator")
st.write("Current processes:", st.session_state.processes)

# ── Algorithm to endpoint mapping ─────────────────────────────────────────────
ALGORITHM_MAP = {
    "FCFS": FCFS_API,
    "SJF Non-Preemptive": SJF_NP_API,
    "SJF Preemptive": SJF_PRE_API,
    "Round Robin": ROUND_ROBIN_API,
    "Priority Non-Preemptive": PRIORITY_NP_API,
    "Priority Preemptive": PRIORITY_PRE_API,
}

# ── Run button ────────────────────────────────────────────────────────────────
if st.button(f"Run {algorithm}"):
    if not st.session_state.processes:
        st.error("Add at least one process before running.")
    else:
        payload = {"processes": st.session_state.processes}
        if algorithm == "Round Robin" and quantum:
            payload["quantum"] = int(quantum)

        with st.spinner("Simulating..."):
            try:
                response = requests.post(
                    ALGORITHM_MAP[algorithm],
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
                st.session_state.last_response = response.json()

            except requests.exceptions.Timeout:
                st.error("Request timed out. Is the backend running?")
                st.session_state.last_response = None

            except requests.exceptions.HTTPError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                st.error(f"API error: {detail}")
                st.session_state.last_response = None

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to the API. Is the backend running?")
                st.session_state.last_response = None

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.last_response is not None:
    st.markdown("---")

    # Gantt chart placeholder — waiting for Visualizer to deliver components/gantt.py
    st.subheader("Gantt Chart")
    st.info("Gantt chart coming in Week 2 — waiting for Visualizer to deliver components/gantt.py")
    # from components.gantt import render_gantt
    # st.plotly_chart(render_gantt(st.session_state.last_response["timeline"], st.session_state.last_response["schedule"]))

    st.markdown("---")

    # Raw response
    st.subheader("Raw API Response")
    st.json(st.session_state.last_response)

# ── Compare Mode ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Compare Mode")
st.info("Compare Mode coming in Week 2 — waiting for /analyze endpoint from Backend Architect.")
# col1, col2, col3, col4 = st.columns(4)
# response = requests.post(ANALYZE_API, json={"processes": st.session_state.processes}, timeout=10)
# results = response.json()