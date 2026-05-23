from fastapi import FastAPI
from schemas import (
    ScheduleRequest, ScheduleResult,
    BankersRequest, BankersResult,
    AnalyzeResult, RecommendResult
)

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
def schedule_fcfs(request: ScheduleResult):
    return mock_schedule_result()