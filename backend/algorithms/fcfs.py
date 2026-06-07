# algorithms/fcfs.py

gantt_chart = []
processes = []
process_count = 0

# while True:
#     process_count += 1
#     arrival_time = float(input("Enter arrival time: "))
#     burst_time = float(input("Enter burst time: "))
#     processes.append({
#         "pid": f"P{process_count}",
#         "arrival_time": arrival_time,
#         "burst_time": burst_time,
#         "priority": 0
#     })
#     if input("Add more entries (y/n): ").lower() != "y":
#         break

def fcfs(processes):
    """
    FCFS — First Come First Served (non-preemptive)

    Input:
        processes: list of dicts, each with:
            pid          (str)
            arrival_time (int)
            burst_time   (int)
            priority     (int) — ignored by FCFS

    Output: dict matching ScheduleResult shape
        schedule             — list of {pid, start, end}
        timeline             — list of {type, pid, start, end}
        avg_waiting_time     — float
        avg_turnaround_time  — float
        cpu_utilization      — float (0–100)
    """
    sorted_processes = sorted(processes, key=lambda t: t["arrival_time"])

    schedule = []
    timeline = []
    current_time = 0
    total_waiting = 0
    total_turnaround = 0
    cpu_busy = 0

    for task in sorted_processes:
        if current_time < task["arrival_time"]:
            timeline.append({
                "type": "idle",
                "pid": None,
                "start": current_time,
                "end": task["arrival_time"]
            })
            current_time = task["arrival_time"]

        start = current_time
        end = current_time + task["burst_time"]

        schedule.append({"pid": task["pid"], "start": start, "end": end})
        timeline.append({"type": "process", "pid": task["pid"], "start": start, "end": end})

        turnaround = end - task["arrival_time"]
        waiting = turnaround - task["burst_time"]
        total_waiting += waiting
        total_turnaround += turnaround
        cpu_busy += task["burst_time"]
        current_time = end

    n = len(processes)
    return {
        "schedule": schedule,
        "timeline": timeline,
        "avg_waiting_time": total_waiting / n,
        "avg_turnaround_time": total_turnaround / n,
        "cpu_utilization": (cpu_busy / current_time) * 100
    }

if __name__ == '__main__':
    result = fcfs(processes)
    print("\nGantt Chart:")
    for ent in result["timeline"]:
        pid = ent["pid"] if ent["pid"] else "idle"
        print(f"  {pid}: {ent['start']} --> {ent['end']}")
    print(f"Avg Waiting Time:    {result['avg_waiting_time']:.2f}")
    print(f"Avg Turnaround Time: {result['avg_turnaround_time']:.2f}")
    print(f"CPU Utilization:     {result['cpu_utilization']:.2f}%")