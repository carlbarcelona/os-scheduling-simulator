# schemas.py

from pydantic import BaseModel, field_validator
from typing import Optional, List

class Process(BaseModel):
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0

    @field_validator("burst_time")
    @classmethod
    def check_burst_time_is_positive(cls, submitted_burst_time):
        if submitted_burst_time <= 0:
            raise ValueError("burst_time must be greater than 0")
        return submitted_burst_time

    @field_validator("arrival_time")
    @classmethod
    def check_arrival_time_is_not_negative(cls, submitted_arrival_time):
        if submitted_arrival_time < 0:
            raise ValueError("arrival_time must be 0 or greater")
        return submitted_arrival_time

class ScheduleRequest(BaseModel):
    processes: List[Process]
    quantum: Optional[int] = None  # Round Robin only

# --- Output models ---

class ScheduledProcess(BaseModel):
    pid: str
    start: int
    end: int

class TimelineBlock(BaseModel):
    type: str       # "process" or "idle"
    pid: Optional[str] = None
    start: int
    end: int

class ScheduleResult(BaseModel):
    schedule: List[ScheduledProcess]
    timeline: List[TimelineBlock]
    avg_waiting_time: float
    avg_turnaround_time: float
    cpu_utilization: float

# --- Analyze ---

class AnalyzeResult(BaseModel):
    results: dict   # keys: "fcfs", "sjf", "rr", "priority"

# --- Banker's Algorithm ---

class BankersRequest(BaseModel):
    allocation: List[List[int]]
    max: List[List[int]]
    available: List[int]
    pid_labels: List[str]

class BankersResult(BaseModel):
    safe: bool
    safe_sequence: List[str]
    reason: str

class RecommendResult(BaseModel):
    best_algorithm: str
    reason: str