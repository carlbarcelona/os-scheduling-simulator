from fastapi import FastAPI
from schemas import *
from algorithm.fcfs import fcfs_example

app = FastAPI(title='Simplified Project Model')

@app.get("/")
def root():
    return {
        "App": "Running"
    }

@app.post("/process-fcfs", response_model=TotalResult)
def run_fcfs(payload: ScheduleProcess):
    # Call the algorithm model
    return (fcfs_example(payload.processes))

