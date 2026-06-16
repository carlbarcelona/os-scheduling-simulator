from functools import reduce

processes = []
process_count = 0

total_memory = int(input("Enter total memory capacity (K): "))
fit_strategy = input("Enter fit strategy (first/best/worst/next): ").lower()

while True:
    process_count += 1
    size = int(input(f"Enter size of Process {process_count} (K): "))
    burst_time = float(input(f"Enter burst time of Process {process_count}: "))
    processes.append({"pid": f"P{process_count}", "size": size, "burst_time": burst_time})
    if input("Add more entries (y/n): ").lower() != "y":
        break

def find_fit_mvt(free_blocks, size, strategy):
    candidates = [(i, b) for i, b in enumerate(free_blocks) if b["free"] and b["size"] >= size]
    if not candidates:
        return None, None
    if strategy == "best":
        return min(candidates, key=lambda x: x[1]["size"])
    elif strategy == "worst":
        return max(candidates, key=lambda x: x[1]["size"])
    return candidates[0]

def mvt(total_memory, processes, fit_strategy):
    free_blocks = [{"start": 0, "size": total_memory, "free": True}]
    timeline = []
    allocated = []
    failed = []
    current_time = 0
    cpu_busy = 0

    # Sort by arrival (burst time used as ordering reference here)
    sorted_processes = sorted(processes, key=lambda p: p["burst_time"])

    def allocate_process(acc, process):
        blocks, alloc_list, fail_list, tl, time, busy = acc
        idx, block = find_fit_mvt(blocks, process["size"], fit_strategy)

        if block is None:
            return blocks, alloc_list, fail_list + [process], tl + [{
                "event": "allocation_failed",
                "pid": process["pid"],
                "time": time,
                "memory_map": [{"pid": b.get("pid", "FREE"), "start": b["start"], "end": b["start"] + b["size"], "free": b["free"]} for b in blocks]
            }], time, busy

        # Allocate block
        alloc = {"start": block["start"], "size": process["size"], "pid": process["pid"], "free": False}
        remaining = block["size"] - process["size"]
        new_blocks = (
            blocks[:idx] +
            [alloc] +
            ([{"start": block["start"] + process["size"], "size": remaining, "free": True}] if remaining > 0 else []) +
            blocks[idx + 1:]
        )

        alloc_entry = {"pid": process["pid"], "start": block["start"], "end": block["start"] + process["size"]}
        new_tl = tl + [{
            "event": "allocated",
            "pid": process["pid"],
            "size": process["size"],
            "burst_time": process["burst_time"],
            "start_time": time,
            "end_time": time + process["burst_time"],
            "memory_map": [{"pid": b.get("pid", "FREE"), "start": b["start"], "end": b["start"] + b["size"], "free": b.get("free", False)} for b in new_blocks]
        }]

        return new_blocks, alloc_list + [alloc_entry], fail_list, new_tl, time + process["burst_time"], busy + process["burst_time"]

    blocks, allocated, failed, timeline, current_time, cpu_busy = reduce(
        allocate_process, sorted_processes, (free_blocks, [], [], [], 0, 0)
    )

    # Simulate removal after burst time
    def remove_process(acc, process):
        blocks, tl, time = acc
        new_blocks = [
            {"start": b["start"], "size": b["size"], "free": True} if b.get("pid") == process["pid"] else b
            for b in blocks
        ]

        # Merge adjacent free blocks
        def merge(merged, block):
            if merged and merged[-1]["free"] and block["free"]:
                return merged[:-1] + [{"start": merged[-1]["start"], "size": merged[-1]["size"] + block["size"], "free": True}]
            return merged + [block]

        merged_blocks = reduce(merge, new_blocks, [])
        new_tl = tl + [{
            "event": "removed",
            "pid": process["pid"],
            "time": time,
            "memory_map": [{"pid": b.get("pid", "FREE"), "start": b["start"], "end": b["start"] + b["size"], "free": b["free"]} for b in merged_blocks]
        }]
        return merged_blocks, new_tl, time

    final_blocks, timeline, _ = reduce(remove_process, sorted_processes, (blocks, timeline, current_time))

    # Final state
    total_free = sum(b["size"] for b in final_blocks if b.get("free", False))
    timeline.append({
        "event": "completed",
        "memory_map": [{"pid": b.get("pid", "FREE"), "start": b["start"], "end": b["start"] + b["size"], "free": b.get("free", False)} for b in final_blocks],
        "total_free": total_free,
        "total_used": 0
    })

    return {
        "strategy": fit_strategy,
        "total_memory": total_memory,
        "allocated": allocated,
        "failed": [p["pid"] for p in failed],
        "timeline": timeline,
        "avg_burst_time": sum(p["burst_time"] for p in processes) / len(processes),
        "cpu_utilization": (cpu_busy / current_time) * 100 if current_time > 0 else 0
    }

result = mvt(total_memory, processes, fit_strategy)
print(f"\n=== MVT Memory Management ({result['strategy'].upper()} Fit) ===")
print(f"Allocated: {[a['pid'] for a in result['allocated']]}")
print(f"Failed: {result['failed'] if result['failed'] else 'None'}")
print(f"Avg Burst Time: {result['avg_burst_time']:.2f}")
print(f"CPU Utilization: {result['cpu_utilization']:.2f}%")
print(f"\nTimeline:")
for entry in result["timeline"]:
    event = entry["event"]
    if event == "allocated":
        print(f"\n  [ALLOCATED] {entry['pid']} | Size: {entry['size']}K | BT: {entry['burst_time']} | {entry['start_time']} --> {entry['end_time']}")
    elif event == "removed":
        print(f"\n  [REMOVED] {entry['pid']} at time {entry['time']}")
    elif event == "allocation_failed":
        print(f"\n  [FAILED] {entry['pid']} at time {entry['time']}")
    elif event == "completed":
        print(f"\n  [COMPLETED] Total Free: {entry['total_free']}K | Total Used: {entry['total_used']}K")
    print(f"  Memory Map: {entry['memory_map']}")