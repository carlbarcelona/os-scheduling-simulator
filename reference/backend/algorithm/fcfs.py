from typing import List
# This is absolutely needed as this is the template for our communication
from schemas import ProcessInput
'''
The payload will have its argument and returning dict shaped below 

Args:
{
  [
    {"pid": "P1", "arrival_time": 0, "burst_time": 8, "priority": 0},
    {"pid": "P2", "arrival_time": 1, "burst_time": 4, "priority": 0}
  ]
}

Return:

{
    "schedule": [
        {"pid": "P1", "start": 0, "end": 8}
    ],
    "timeline": [
        {"type": "process", "pid": "P1", "start": 0, "end": 8},
        {"type": "idle", "pid": None, "start": 8, "end": 10}
    ],
    "avg_waiting_time": 4.0,
    "avg_turnaround_time": 10.0,
    "cpu_utilization": 100.0
}
'''


def fcfs_example(processes: List[ProcessInput]):
    # Insert algorithm

    # For the sake of this model, let's just return the sample payload
    return {
    "schedule": [
        {"pid": "P1", "start": 0, "end": 8}
    ],
    "timeline": [
        {"type": "process", "pid": "P1", "start": 0, "end": 8},
        {"type": "idle", "pid": "IDLE", "start": 8, "end": 10} # Insert an IDLE string if CPU is idle 
    ],
    "avg_waiting_time": 4.0,
    "avg_turnaround_time": 10.0,
    "cpu_utilization": 100.0
    }