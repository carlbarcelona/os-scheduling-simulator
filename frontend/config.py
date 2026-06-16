import os
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# -- For POST ops -- 

# CPU Scheduling APIs
FCFS_API = f"{API_BASE}/schedule/fcfs"
SJF_NP_API = f"{API_BASE}/schedule/sjf_np"
SJF_PRE_API = f"{API_BASE}/schedule/sjf_pre"
PRIORITY_PRE_API = f"{API_BASE}/schedule/priority_pre"
PRIORITY_NP_API = f"{API_BASE}/schedule/priority_np"
ROUND_ROBIN_API = f"{API_BASE}/schedule/round_robin"
MLFQ_API = f"{API_BASE}/schedule/mlfq" # Empty
SCHEDULE_ANALYZE_API = f"{API_BASE}/schedule/analyze"

# Mass storage management APIS
DISK_FCFS_API  = f"{API_BASE}/disk/fcfs"
DISK_SSTF_API  = f"{API_BASE}/disk/sstf"    
DISK_SCAN_API  = f"{API_BASE}/disk/scan"
DISK_CSCAN_API = f"{API_BASE}/disk/cscan"
DISK_LOOK_API  = f"{API_BASE}/disk/look"
DISK_CLOOK_API = f"{API_BASE}/disk/clook"
DISK_ANALYZE_API = f"{API_BASE}/disk/analyze" # Not yet implemented