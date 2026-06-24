# main.py
from fastapi import FastAPI
from schemas import *

# For CPU Scheduling
from algorithms.cpu_scheduling.fcfs import fcfs
from algorithms.cpu_scheduling.sjf_nonpree import sjf_non_preemptive
from algorithms.cpu_scheduling.sjf_pree import sjf_preemptive
from algorithms.cpu_scheduling.priority_pree import priority_preemptive
from algorithms.cpu_scheduling.priority_nonpree import priority_non_preemptive
from algorithms.cpu_scheduling.round_robin import round_robin
# from algorithms.cpu_scheduling.mlfq import mlfq  # mlfq.py not implemented yet

# For Mass Storage
from algorithms.mass_storage.fcfs_disk import fcfs_disk
from algorithms.mass_storage.sstf_disk import sstf_disk
from algorithms.mass_storage.c_look import clook_disk
from algorithms.mass_storage.c_scan_disk import cscan_disk
from algorithms.mass_storage.look_disk import look_disk
from algorithms.mass_storage.scan_disk import scan_disk

app = FastAPI(title="CPU Scheduling Simulator")

@app.get("/")
def root():
    return {"status": "ok",
    "message": "OS Simulator Up and Running"}

# ─────────────────────────────────────────
# CPU SCHEDULING
# ─────────────────────────────────────────
@app.post("/schedule/fcfs", response_model=ScheduleResult)
def schedule_fcfs(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return fcfs(processes)

@app.post("/schedule/sjf_pre", response_model=ScheduleResult)
def schedule_pre_sjf(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return sjf_preemptive(processes)

@app.post("/schedule/sjf_np", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return sjf_non_preemptive(processes)

@app.post("/schedule/priority_pre", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return priority_preemptive(processes)

@app.post("/schedule/priority_np", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return priority_non_preemptive(processes)

@app.post("/schedule/round_robin", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return round_robin(processes)

@app.post("/schedule/analyze", response_model=ScheduleAnalyzeResult)
def disk_analyze(request: ScheduleRequest):
    """Runs all disk algorithms on the same input for comparison."""
    pass # Empty

# ─────────────────────────────────────────
# MASS STORAGE — DISK SCHEDULING
# ─────────────────────────────────────────

@app.post("/disk/fcfs", response_model=DiskResult)
def disk_fcfs(request: DiskRequest):
    return fcfs_disk(
        head = request.head,
        requests = request.requests,
        number_of_tracks = request.number_of_tracks,
    )

@app.post("/disk/sstf", response_model=DiskResult)
def disk_sstf(request: DiskRequest):
    return sstf_disk(
        head = request.head,
        requests = request.requests,
        number_of_tracks = request.number_of_tracks,
    )



@app.post("/disk/scan", response_model=DiskResult)
def disk_scan(request: DiskRequest):
    return scan_disk(
        head = request.head,
        requests = request.requests,
        direction = request.direction,
        number_of_tracks = request.number_of_tracks,
    )
 
@app.post("/disk/cscan", response_model=DiskResult)
def disk_cscan(request: DiskRequest):
    return cscan_disk(
        head  = request.head,
        requests = request.requests,
        direction  = request.direction,
        number_of_tracks = request.number_of_tracks,
    )
 
@app.post("/disk/look", response_model=DiskResult)
def disk_look(request: DiskRequest):
    return look_disk(
        head = request.head,
        requests = request.requests,
        direction = request.direction,
        number_of_tracks = request.number_of_tracks,
    )
 
@app.post("/disk/clook", response_model=DiskResult)
def disk_clook(request: DiskRequest):
    return clook_disk(
        head      = request.head,
        requests  = request.requests,
        direction = request.direction,
        number_of_tracks = request.number_of_tracks,
    )

@app.post("/disk/analyze", response_model=DiskAnalyzeResult)
def disk_analyze(request: DiskRequest):
    """Runs all disk algorithms on the same input for comparison."""
    pass # Empty