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
DISK_ANALYZE_API = f"{API_BASE}/disk/analyze"

# Memory management APIs
MEMORY_MVT_WITH_COMPACTION_API    = f"{API_BASE}/memory/mvt_with_compaction"
MEMORY_MVT_WITHOUT_COMPACTION_API = f"{API_BASE}/memory/mvt_without_compaction"

# Virtual memory — page replacement APIs
VM_FIFO_API       = f"{API_BASE}/vm/fifo"
VM_LRU_API        = f"{API_BASE}/vm/lru"
VM_LRU_APPROX_API = f"{API_BASE}/vm/lru_approx"
VM_OPTIMAL_API    = f"{API_BASE}/vm/optimal"
VM_LFU_API        = f"{API_BASE}/vm/lfu"
VM_MFU_API        = f"{API_BASE}/vm/mfu"