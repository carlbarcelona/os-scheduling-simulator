from pydantic import BaseModel
from typing import List, Optional

class ProcessInput(BaseModel):
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0

class ScheduleProcess(BaseModel):
    processes: List[ProcessInput]

class ScheduleResult(BaseModel):
    pid: str
    start: int
    end: int

class TimelineResult(BaseModel):
    type: str
    pid: str
    start: int
    end: int

class TotalResult(BaseModel):
    schedule: List[ScheduleResult]
    timeline: List[TimelineResult]
    avg_waiting_time: float
    avg_turnaround_time: float
    cpu_utilization: float

