gantt_chart = []
processes = []
process_count = 0

while True:
    process_count += 1
    arrival_time = float(input("Enter arrival time: "))
    burst_time = float(input("Enter burst time: "))
    processes.append({
        "pid": f"P{process_count}",
        "arrival_time": arrival_time,
        "burst_time": burst_time,
        "priority": 0
    })
    if input("Add more entries (y/n): ").lower() != "y":
        break

def sjf_preemptive(processes):
    remaining = [{**t, "remaining_time": t["burst_time"]} for t in processes]

    schedule = []
    timeline = []
    current_time = 0
    total_waiting = 0
    total_turnaround = 0
    cpu_busy = 0

    while remaining:
        available = [t for t in remaining if t["arrival_time"] <= current_time]

        if not available:
            next_arrival = min(remaining, key=lambda t: t["arrival_time"])
            timeline.append({
                "type": "idle",
                "pid": None,
                "start": current_time,
                "end": next_arrival["arrival_time"]
            })
            current_time = next_arrival["arrival_time"]
            continue

        task = min(available, key=lambda t: t["remaining_time"])

        task["remaining_time"] -= 1
        current_time += 1
        cpu_busy += 1

        if timeline and timeline[-1]["type"] == "process" and timeline[-1]["pid"] == task["pid"]:
            timeline[-1]["end"] = current_time
        else:
            timeline.append({
                "type": "process",
                "pid": task["pid"],
                "start": current_time - 1,
                "end": current_time
            })

        if task["remaining_time"] == 0:
            turnaround = current_time - task["arrival_time"]
            waiting = turnaround - task["burst_time"]
            total_waiting += waiting
            total_turnaround += turnaround

            task_timeline = [t for t in timeline if t.get("pid") == task["pid"]]
            schedule.append({
                "pid": task["pid"],
                "start": task_timeline[0]["start"],
                "end": current_time
            })
            remaining.remove(task)

    n = len(processes)
    return {
        "schedule": schedule,
        "timeline": timeline,
        "avg_waiting_time": total_waiting / n,
        "avg_turnaround_time": total_turnaround / n,
        "cpu_utilization": (cpu_busy / current_time) * 100
    }

result = sjf_preemptive(processes)
print("\nGantt Chart:")
for ent in result["timeline"]:
    pid = ent["pid"] if ent["pid"] else "idle"
    print(f"  {pid}: {ent['start']} --> {ent['end']}")
print(f"Avg Waiting Time:    {result['avg_waiting_time']:.2f}")
print(f"Avg Turnaround Time: {result['avg_turnaround_time']:.2f}")
print(f"CPU Utilization:     {result['cpu_utilization']:.2f}%")