# frontend/app.py

import streamlit as st
import requests
from config import *

# Session state initialization
if "processes" not in st.session_state:
    st.session_state.processes = []

# Sidebar form
st.sidebar.title("Add Process")
pid = st.sidebar.text_input("Process ID")
arrival_time = st.sidebar.number_input("Arrival Time", min_value=0, step=1)
burst_time = st.sidebar.number_input("Burst Time", min_value=1, step=1)

if st.sidebar.button("Add Process"):
    st.session_state.processes.append({
        "pid": pid,
        "arrival_time": int(arrival_time),
        "burst_time": int(burst_time),
    })

# Main area
st.title("CPU Scheduling Simulator")
st.write("Current processes:", st.session_state.processes)

# Run FCFS
if st.button("Run SJF NP"):
    response = requests.post(
        SJF_NP_API,
        json={"processes": st.session_state.processes}
    )
    st.json(response.json())