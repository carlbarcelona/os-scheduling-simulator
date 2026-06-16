# schemas.py

from pydantic import BaseModel, field_validator
from typing import Optional, List

# ─────────────────────────────────────────
# CU Sheduling — DISK SCHEDULING
# ─────────────────────────────────────────

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
    """
    Input for CPU scheduling algorithms.

    Ex:

    # {
    #   "processes": [
    #     {"pid": "P1", "arrival_time": 0, "burst_time": 8},
    #     {"pid": "P2", "arrival_time": 1, "burst_time": 4},
    #     {"pid": "P3", "arrival_time": 2, "burst_time": 9, "priority": 2}
    #   ],
    #   "quantum": 3    ← Round Robin and MLFQ only. Omit for all others.
    # }
    #

    """
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
    '''
    # {
    #   "schedule": [
    #     {"pid": "P1", "start": 0, "end": 8},
    #     {"pid": "P2", "start": 8, "end": 12}
    #   ],
    #   "timeline": [
    #     {"type": "process", "pid": "P1", "start": 0,  "end": 8},
    #     {"type": "idle",    "pid": null,  "start": 8,  "end": 9},
    #     {"type": "process", "pid": "P2", "start": 9,  "end": 13}
    #   ],
    #   "avg_waiting_time":    4.0,
    #   "avg_turnaround_time": 10.0,
    #   "cpu_utilization":     100.0
    # }
    #
    '''
    schedule: List[ScheduledProcess]
    timeline: List[TimelineBlock]
    avg_waiting_time: float
    avg_turnaround_time: float
    cpu_utilization: float

# --- Analyze ---

class ScheduleAnalyzeResult(BaseModel):
    results: dict   # keys: "fcfs", "sjf", "rr", "priority"

# ─────────────────────────────────────────
# MASS STORAGE — DISK SCHEDULING
# ─────────────────────────────────────────

class DiskRequest(BaseModel):
    """
    Input for all disk scheduling algorithms.

    head              — starting head position
    requests          — list of cylinder numbers to service
    number_of_tracks  — total cylinders on disk (required by SCAN and C-SCAN)
    direction         — "left" or "right" (Optional for some algos)
    """
    head:             int
    requests:         List[int]
    number_of_tracks: int
    direction:        str = "right"          # can be ignored

    @field_validator("head")
    @classmethod
    def check_head_not_negative(cls,  value):
        if  value < 0:
            raise ValueError("head must be 0 or greater")
        return  value

    @field_validator("requests")
    @classmethod
    def check_requests_not_empty(cls, value):
        if len( value) == 0:
            raise ValueError("requests list cannot be empty")
        return  value

    @field_validator("direction")
    @classmethod
    def check_direction_valid(cls, value):
        if  value not in ("left", "right"):
            raise ValueError("direction must be 'left' or 'right'")
        return  value

# --- Output models ---

class DiskMovement(BaseModel):
    from_cylinder: int
    to_cylinder:   int
    distance:      int


class DiskResult(BaseModel):
    """
    Returned by every disk scheduling algorithm.

    initial_head        — starting head position
    sequence            — full ordered list of cylinders visited
    movements           — step-by-step head movement breakdown
    total_head_movement — sum of all distances (key comparison metric)
    """
    initial_head:        int
    sequence:            List[int]
    movements:           List[DiskMovement]
    total_head_movement: int

# --- Analyze ---

class DiskAnalyzeResult(BaseModel):
    results: dict       # keys: "fcfs", "sstf", "scan", "cscan", "look", "clook"