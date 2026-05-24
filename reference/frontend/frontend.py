import streamlit as st
import requests
from config import *

st.title("Simplified Simulator")

# 1. Establish a default starting row (Concept: Seed Data)
default_rows = [
    {"pid": "P1", "arrival_time": 0, "burst_time": 8, "priority": 0},
    {"pid": "P2", "arrival_time": 1, "burst_time": 4, "priority": 0},
]

st.write("Edit your process sequence below:")

# 2. Render the interactive spreadsheet grid
# 'num_rows="dynamic"' allows users to hit a '+' button to add new rows!
edited_data = st.data_editor(default_rows, num_rows="dynamic")

if st.button("Submit all Tasks to Backend"):
    # Package the edited spreadsheet data under a single dictionary key
    # The "processes" key is important as that categorizes the payload
    payload = {"processes": edited_data}
    
    try:
        response = requests.post(f"{API_BASE}/process-fcfs", json=payload)
        st.success("Backend Response Received!")
        st.json(response.json())
    except requests.exceptions.ConnectionError:
        st.error("Is your FastAPI backend running?")
        st.json(response.json())