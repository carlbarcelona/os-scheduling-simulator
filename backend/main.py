# main.py

from fastapi import FastAPI
from schemas import (
    ScheduleRequest, ScheduleResult,
    BankersRequest, BankersResult,
    AnalyzeResult, RecommendResult
)

from algorithms.fcfs import *

app = FastAPI(title="CPU Scheduling Simulator")

@app.get("/")
def root():
    return {"status": "ok",
    "message": "CPU Scheduling Simulator Up and Running"}

def mock_schedule_result():
    return {
        "schedule": [{"pid": "P1", "start": 0, "end": 8}],
        "timeline": [{"type": "process", "pid": "P1", "start": 0, "end": 8}],
        "avg_waiting_time": 0.0,
        "avg_turnaround_time": 8.0,
        "cpu_utilization": 100.0
    }

@app.post("/schedule/fcfs", response_model=ScheduleResult)
def schedule_fcfs(request: ScheduleRequest):
    processes = [details.model_dump() for details in request.processes]
    return fcfs(processes)

@app.post("/schedule/sjf_pre", response_model=ScheduleResult)
def schedule_pre_sjf(request: ScheduleRequest):
    return mock_schedule_result()

@app.post("/schedule/sjf_np", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    return mock_schedule_result()

@app.post("/schedule/priority_pre", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    return mock_schedule_result()

@app.post("/schedule/priority_np", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    return mock_schedule_result()

@app.post("/schedule/round_robin", response_model=ScheduleResult)
def schedule_np_sjf(request: ScheduleRequest):
    return mock_schedule_result()