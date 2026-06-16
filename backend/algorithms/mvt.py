from functools import reduce

total_memory = int(input("Enter total memory capacity (K): "))
fit_strategy = input("Enter fit strategy (first/best/worst/next): ").lower()
processes = []
process_count = 0
while True:
    process_count += 1
    pid = f"P{process_count}"
    size = int(input(f"Enter size of {pid} (K): "))
    burst_time = float(input(f"Enter burst time of {pid}: "))
    processes.append({"pid": pid, "size": size, "burst_time": burst_time})
    if input("Add more entries (y/n): ").lower() != "y":
        break

data = {"total_memory": total_memory, "fit_strategy": fit_strategy, "processes": processes}

def snapshot(blocks):
    return [{"pid": b.get("pid", "FREE"), "start": b["start"], "end": b["start"] + b["size"], "free": b.get("free", True)} for b in blocks]

def find_fit(blocks, size, strategy):
    candidates = [(i, b) for i, b in enumerate(blocks) if b.get("free", False) and b["size"] >= size]
    if not candidates:
        return None, None
    if strategy == "best":
        return min(candidates, key=lambda x: x[1]["size"])
    elif strategy == "worst":
        return max(candidates, key=lambda x: x[1]["size"])
    return candidates[0]

def allocate(blocks, process, strategy, current_time):
    idx, block = find_fit(blocks, process["size"], strategy)
    if block is None:
        return blocks, None, {"event": "allocation_failed", "pid": process["pid"], "time": current_time, "memory_map": snapshot(blocks)}
    remaining = block["size"] - process["size"]
    new_blocks = (
        blocks[:idx] +
        [{"start": block["start"], "size": process["size"], "pid": process["pid"], "free": False}] +
        ([{"start": block["start"] + process["size"], "size": remaining, "free": True}] if remaining > 0 else []) +
        blocks[idx+1:]
    )
    return new_blocks, {"pid": process["pid"], "start": block["start"], "end": block["start"] + process["size"]}, {"event": "allocated", "pid": process["pid"], "size": process["size"], "burst_time": process["burst_time"], "start_time": current_time, "end_time": current_time + process["burst_time"], "memory_map": snapshot(new_blocks)}

def merge_free(blocks):
    def merge(acc, block):
        if acc and acc[-1].get("free") and block.get("free"):
            return acc[:-1] + [{"start": acc[-1]["start"], "size": acc[-1]["size"] + block["size"], "free": True}]
        return acc + [block]
    return reduce(merge, blocks, [])

def remove_process(blocks, pid, current_time):
    new_blocks = merge_free([{"start": b["start"], "size": b["size"], "free": True} if b.get("pid") == pid else b for b in blocks])
    return new_blocks, {"event": "removed", "pid": pid, "time": current_time, "memory_map": snapshot(new_blocks)}

def mvt_without_compaction(data):
    blocks = [{"start": 0, "size": data["total_memory"], "free": True}]
    strategy, processes = data["fit_strategy"], data["processes"]
    timeline, allocated_list, failed_list = [], [], []
    current_time, cpu_busy = 0, 0

    for process in processes:
        blocks, alloc_entry, event = allocate(blocks, process, strategy, current_time)
        timeline.append(event)
        if alloc_entry:
            allocated_list.append(alloc_entry)
            current_time += process["burst_time"]
            cpu_busy += process["burst_time"]
        else:
            failed_list.append(process["pid"])

    for process in sorted(processes, key=lambda p: p["burst_time"]):
        if process["pid"] not in failed_list:
            blocks, event = remove_process(blocks, process["pid"], current_time)
            timeline.append(event)

    total_free = sum(b["size"] for b in blocks if b.get("free", False))
    timeline.append({"event": "completed", "memory_map": snapshot(blocks), "total_free": total_free, "total_used": 0})

    return {
        "strategy": strategy,
        "total_memory": data["total_memory"],
        "allocated": allocated_list,
        "failed": failed_list,
        "avg_burst_time": round(sum(p["burst_time"] for p in processes) / len(processes), 2),
        "cpu_utilization": round((cpu_busy / current_time) * 100, 2) if current_time > 0 else 0,
        "timeline": timeline
    }

def mvt_with_compaction(data):
    blocks = [{"start": 0, "size": data["total_memory"], "free": True}]
    strategy, processes = data["fit_strategy"], data["processes"]
    timeline, allocated_list, failed_list, retry_list = [], [], [], []
    current_time, cpu_busy = 0, 0

    for process in processes:
        blocks, alloc_entry, event = allocate(blocks, process, strategy, current_time)
        timeline.append(event)
        if alloc_entry:
            allocated_list.append(alloc_entry)
            current_time += process["burst_time"]
            cpu_busy += process["burst_time"]
        else:
            failed_list.append(process)

    # Compaction: move all used blocks together
    if failed_list:
        used = [b for b in blocks if not b.get("free", False)]
        total_free = sum(b["size"] for b in blocks if b.get("free", False))
        cursor = 0
        compacted = []
        for b in used:
            compacted.append({**b, "start": cursor})
            cursor += b["size"]
        if total_free > 0:
            compacted.append({"start": cursor, "size": total_free, "free": True})
        blocks = compacted
        timeline.append({"event": "compacted", "time": current_time, "memory_map": snapshot(blocks)})

        for process in failed_list:
            blocks, alloc_entry, event = allocate(blocks, process, strategy, current_time)
            event["event"] = "retry_allocated" if alloc_entry else "allocation_failed"
            timeline.append(event)
            if alloc_entry:
                allocated_list.append(alloc_entry)
                retry_list.append(process["pid"])
                current_time += process["burst_time"]
                cpu_busy += process["burst_time"]

    all_allocated_pids = [a["pid"] for a in allocated_list]
    for process in sorted([p for p in processes if p["pid"] in all_allocated_pids], key=lambda p: p["burst_time"]):
        blocks, event = remove_process(blocks, process["pid"], current_time)
        timeline.append(event)

    total_free = sum(b["size"] for b in blocks if b.get("free", False))
    timeline.append({"event": "completed", "memory_map": snapshot(blocks), "total_free": total_free, "total_used": 0})

    return {
        "strategy": strategy,
        "total_memory": data["total_memory"],
        "allocated": allocated_list,
        "failed": [p["pid"] for p in failed_list],
        "compaction_performed": len(failed_list) > 0,
        "retry_allocated": retry_list,
        "avg_burst_time": round(sum(p["burst_time"] for p in processes) / len(processes), 2),
        "cpu_utilization": round((cpu_busy / current_time) * 100, 2) if current_time > 0 else 0,
        "timeline": timeline
    }

def print_mvt(result, title):
    print(f"\n=== {title} ({result['strategy'].upper()} Fit) ===")
    print(f"Allocated: {[a['pid'] for a in result['allocated']]}")
    print(f"Failed:    {result['failed'] if result['failed'] else 'None'}")
    if "retry_allocated" in result:
        print(f"Retry Allocated: {result['retry_allocated']}")
    print(f"Avg Burst Time:  {result['avg_burst_time']}")
    print(f"CPU Utilization: {result['cpu_utilization']}%")
    print(f"\nTimeline:")
    for entry in result["timeline"]:
        event = entry["event"]
        if event == "allocated":
            print(f"\n  [ALLOCATED]  {entry['pid']} | Size: {entry['size']}K | BT: {entry['burst_time']} | {entry['start_time']} --> {entry['end_time']}")
        elif event == "retry_allocated":
            print(f"\n  [RETRY]      {entry['pid']} | Size: {entry['size']}K | BT: {entry['burst_time']} | {entry['start_time']} --> {entry['end_time']}")
        elif event == "allocation_failed":
            print(f"\n  [FAILED]     {entry['pid']} at time {entry['time']}")
        elif event == "compacted":
            print(f"\n  [COMPACTED]  at time {entry['time']}")
        elif event == "removed":
            print(f"\n  [REMOVED]    {entry['pid']} at time {entry['time']}")
        elif event == "completed":
            print(f"\n  [COMPLETED]  Total Free: {entry['total_free']}K | Total Used: {entry['total_used']}K")
        print(f"  Memory Map: {entry['memory_map']}")

print_mvt(mvt_without_compaction(data), "MVT Without Compaction")
print_mvt(mvt_with_compaction(data), "MVT With Compaction")