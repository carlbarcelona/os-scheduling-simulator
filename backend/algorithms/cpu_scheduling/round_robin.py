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

# quantum = int(input("Enter time quantum: "))

def round_robin(processes, quantum=2):
    remaining = [{**t, "remaining_time": t["burst_time"]} for t in processes]
    remaining.sort(key=lambda t: t["arrival_time"])

    schedule = []
    timeline = []
    current_time = 0
    total_waiting = 0
    total_turnaround = 0
    cpu_busy = 0
    queue = []
    visited = set()

    # Enqueue first arrived process
    for t in remaining:
        if t["arrival_time"] <= current_time and t["pid"] not in visited:
            queue.append(t)
            visited.add(t["pid"])

    while queue or any(t["remaining_time"] > 0 for t in remaining):
        if not queue:
            # Idle period — jump to next unfinished arrival
            next_task = min(
                [t for t in remaining if t["remaining_time"] > 0],
                key=lambda t: t["arrival_time"]
            )
            timeline.append({
                "type": "idle",
                "pid": None,
                "start": current_time,
                "end": next_task["arrival_time"]
            })
            current_time = next_task["arrival_time"]

            # Enqueue newly arrived processes
            for t in remaining:
                if t["arrival_time"] <= current_time and t["pid"] not in visited and t["remaining_time"] > 0:
                    queue.append(t)
                    visited.add(t["pid"])
            continue

        task = queue.pop(0)

        # Run for quantum or remaining time, whichever is smaller
        run_time = min(quantum, task["remaining_time"])
        start = current_time
        end = current_time + run_time

        task["remaining_time"] -= run_time
        current_time = end
        cpu_busy += run_time

        schedule.append({"pid": task["pid"], "start": start, "end": end})
        timeline.append({"type": "process", "pid": task["pid"], "start": start, "end": end})

        # Enqueue newly arrived processes during this quantum
        for t in remaining:
            if t["arrival_time"] <= current_time and t["pid"] not in visited and t["remaining_time"] > 0:
                queue.append(t)
                visited.add(t["pid"])

        if task["remaining_time"] == 0:
            turnaround = current_time - task["arrival_time"]
            waiting = turnaround - task["burst_time"]
            total_waiting += waiting
            total_turnaround += turnaround
        else:
            # Re-enqueue unfinished task at the back
            queue.append(task)

    n = len(processes)
    return {
        "schedule": schedule,
        "timeline": timeline,
        "avg_waiting_time": total_waiting / n,
        "avg_turnaround_time": total_turnaround / n,
        "cpu_utilization": (cpu_busy / current_time) * 100
    }

# result = round_robin(processes, quantum)
# print("\nGantt Chart:")
# for ent in result["timeline"]:
#     pid = ent["pid"] if ent["pid"] else "idle"
#     print(f"  {pid}: {ent['start']} --> {ent['end']}")
# print(f"Avg Waiting Time:    {result['avg_waiting_time']:.2f}")
# print(f"Avg Turnaround Time: {result['avg_turnaround_time']:.2f}")
# print(f"CPU Utilization:     {result['cpu_utilization']:.2f}%")