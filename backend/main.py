# main.py
from fastapi import FastAPI
from schemas import *
import advisor

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

# For Memory Management (MVT)
from algorithms.virtual_memory.mvt import mvt_with_compaction, mvt_without_compaction

# For Virtual Memory (Page Replacement)
from algorithms.page_replacement.fifo_pra import fifo_pra
from algorithms.page_replacement.lru_pra import lru_pra
from algorithms.page_replacement.lru_approx_pra import lru_approximation_pra
from algorithms.page_replacement.optimal_pra import optimal_pra
from algorithms.page_replacement.lfu import lfu_pra
from algorithms.page_replacement.mfu import mfu_pra

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
def schedule_priority_pre(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return priority_preemptive(processes)

@app.post("/schedule/priority_np", response_model=ScheduleResult)
def schedule_priority_np(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return priority_non_preemptive(processes)

@app.post("/schedule/round_robin", response_model=ScheduleResult)
def schedule_round_robin(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return round_robin(processes, request.quantum or 2)

@app.post("/schedule/analyze", response_model=ScheduleAnalyzeResult)
def schedule_analyze(request: ScheduleRequest):
    """Runs all CPU scheduling algorithms on the same input for comparison."""
    processes = [details.model_dump() for details in request.processes]
    return {"results": advisor.analyze_cpu(processes, request.quantum or 2)}

@app.post("/schedule/recommend", response_model=RecommendResult)
def schedule_recommend(request: ScheduleRequest):
    """Detects workload properties and recommends a CPU scheduling algorithm."""
    processes = [details.model_dump() for details in request.processes]
    return advisor.recommend_cpu(processes, request.quantum or 2)

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
    return {"results": advisor.analyze_disk(
        head=request.head,
        requests=request.requests,
        direction=request.direction,
        number_of_tracks=request.number_of_tracks,
    )}

@app.post("/disk/recommend", response_model=RecommendResult)
def disk_recommend(request: DiskRequest):
    """Detects request-pattern properties and recommends a disk scheduling algorithm."""
    return advisor.recommend_disk(
        head=request.head,
        requests=request.requests,
        direction=request.direction,
        number_of_tracks=request.number_of_tracks,
    )

# ─────────────────────────────────────────
# MEMORY MANAGEMENT — MVT
# ─────────────────────────────────────────

@app.post("/memory/mvt_with_compaction")
def memory_mvt_with_compaction(request: MemoryRequest):
    return mvt_with_compaction(request.model_dump())

@app.post("/memory/mvt_without_compaction")
def memory_mvt_without_compaction(request: MemoryRequest):
    return mvt_without_compaction(request.model_dump())

@app.post("/memory/analyze", response_model=MemoryAnalyzeResult)
def memory_analyze(request: MemoryAnalyzeRequest):
    """Compares First/Best/Worst fit on the same workload (compaction selectable)."""
    processes = [p.model_dump() for p in request.processes]
    return {"results": advisor.analyze_memory(request.total_memory, processes, request.compaction)}

# ─────────────────────────────────────────
# VIRTUAL MEMORY — PAGE REPLACEMENT
# ─────────────────────────────────────────

@app.post("/vm/fifo")
def vm_fifo(request: PageReplacementRequest):
    return fifo_pra(request.model_dump())

@app.post("/vm/lru")
def vm_lru(request: PageReplacementRequest):
    return lru_pra(request.model_dump())

@app.post("/vm/lru_approx")
def vm_lru_approx(request: PageReplacementRequest):
    return lru_approximation_pra(request.model_dump())

@app.post("/vm/optimal")
def vm_optimal(request: PageReplacementRequest):
    return optimal_pra(request.model_dump())

@app.post("/vm/lfu")
def vm_lfu(request: PageReplacementRequest):
    return lfu_pra(request.model_dump())

@app.post("/vm/mfu")
def vm_mfu(request: PageReplacementRequest):
    return mfu_pra(request.model_dump())

@app.post("/vm/analyze", response_model=VMAnalyzeResult)
def vm_analyze(request: PageReplacementRequest):
    """Runs all page-replacement algorithms on the same reference string."""
    return {"results": advisor.analyze_vm(request.pages, request.frames)}