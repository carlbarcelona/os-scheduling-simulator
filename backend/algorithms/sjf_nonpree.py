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
remaining_task = all_task.copy()

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
    task = min(available, key=lambda t: t["burst_time"])

    #Current process time (start--->finish)
    start_time = current_time
    end_time = current_time + task["burst_time"]

    #Updating the gantt chart
    gantt_chart.append({
        "process_name": task["process_name"],
        "start_time": start_time,
        "end_time": end_time
    })

    #Turn around time and waiting per task
    task["start_time"] = start_time
    task["end_time"] = end_time
    task["turnaround_time"] = end_time - task["arrival_time"]
    task["waiting_time"] = task["turnaround_time"] - task["burst_time"]

    #Ending process
    current_time = end_time
    remaining_task.remove(task)

#Outputs (terminal only)
print("Gantt Chart:")
for ent in gantt_chart:
    print(f" {ent['process_name']}: {ent['start_time']} --> {ent['end_time']}")

print("Process Details:")
for task in all_task:
    print(f"{task['process_name']} | AT: {task['arrival_time']} | BT: {task['burst_time']} | TAT: {task['turnaround_time']} | WT:{task['waiting_time']}")

