gantt_chart = []
all_task = []
process_count = 0 

while True:
    #Number of processes
    process_count += 1
    
    #Entering new entry
    arrival_time = float(input("Enter arrival time: "))
    burst_time = float(input("Enter burst time: "))
    all_task.append({
        "process_name": f"P{process_count}", 
        "arrival_time": arrival_time, 
        "burst_time": burst_time
    })

    #Adding more entries 
    if input("Add more entries (y/n): ").lower() != "y":
        break
    
#Sorting list to first arrival
all_task.sort(key=lambda t: t["arrival_time"])

#Processing Time
current_time = 0
remaining_task = [{**t, "remaining_time": t["burst_time"]} for t in all_task]

while remaining_task:
    #Get all task available 
    available = [t for t in remaining_task if t["arrival_time"] <= current_time]

    #If the CPU is idle
    if not available:
        next_arrival = min(remaining_task, key=lambda t: t["arrival_time"])
        gantt_chart.append({
            "process_name": "idle",
            "start_time": current_time,
            "end_time": next_arrival["arrival_time"]
        })
        current_time = next_arrival["arrival_time"]
        continue
    
    #Choosing shortest job available
    task = min(available, key=lambda t: t["remaining_time"])

    #Rechecks available task every second
    task["remaining_time"] -= 1
    current_time += 1

    #Updating the gantt chart
    if gantt_chart and gantt_chart[-1]["process_name"] == task["process_name"]:
        gantt_chart[-1]["end_time"] = current_time
    else:
        gantt_chart.append({
            "process_name": task["process_name"],
            "start_time": current_time - 1,
            "end_time": current_time
        })

    #Turn around time and waiting time per task
    if task["remaining_time"] == 0:
        task["end_time"] = current_time
        task["turnaround_time"] = current_time - task["arrival_time"]
        task["waiting_time"] = task["turnaround_time"] - task["burst_time"]

        for og in all_task:
            if og["process_name"] == task["process_name"]:
                og["turnaround_time"] = task["turnaround_time"]
                og["waiting_time"] = task["waiting_time"]
                break

        #Ending process
        remaining_task.remove(task)

#Outputs (terminal only)
print("Gantt Chart:")
for ent in gantt_chart:
    print(f" {ent['process_name']}: {ent['start_time']} --> {ent['end_time']}")

print("Process Details:")
for task in all_task:
    print(f"{task['process_name']} | AT: {task['arrival_time']} | BT: {task['burst_time']} | TAT: {task['turnaround_time']} | WT:{task['waiting_time']}")

