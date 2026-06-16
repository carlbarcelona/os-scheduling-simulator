import os
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# -- For POST -- 
# CPU Scheduling APIs
FCFS_API = f"{API_BASE}/schedule/fcfs"
SJF_NP_API = f"{API_BASE}/schedule/sjf_np"
SJF_PRE_API = f"{API_BASE}/schedule/sjf_pre"
PRIORITY_PRE_API = f"{API_BASE}/schedule/priority_pre"
PRIORITY_NP_API = f"{API_BASE}/schedule/priority_np"
ROUND_ROBIN_API = f"{API_BASE}/schedule/round_robin"
MLFQ_API = f"{API_BASE}/schedule/mlfq" # Empty