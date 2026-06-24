from functools import reduce

def find_partition_mft(partitions, size, strategy):
    candidates = [(i, p) for i, p in enumerate(partitions) if p["free"] and p["size"] >= size]
    if not candidates:
        return None, None
    if strategy == "best":
        return min(candidates, key=lambda x: x[1]["size"] - size)
    elif strategy == "worst":
        return max(candidates, key=lambda x: x[1]["size"] - size)
    return candidates[0]

def mft(total_memory, partition_size, processes, fit_strategy):
    num_partitions = total_memory // partition_size
    partitions = [
        {"id": i + 1, "start": i * partition_size, "size": partition_size, "pid": None, "free": True, "internal_frag": 0}
        for i in range(num_partitions)
    ]
    timeline = []
    allocated = []
    failed = []
    current_time = 0
    cpu_busy = 0

    sorted_processes = sorted(processes, key=lambda p: p["burst_time"])

    def allocate_process(acc, process):
        parts, alloc_list, fail_list, tl, time, busy = acc
        idx, partition = find_partition_mft(parts, process["size"], fit_strategy)

        if partition is None:
            return parts, alloc_list, fail_list + [process], tl + [{
                "event": "allocation_failed",
                "pid": process["pid"],
                "time": time,
                "memory_map": [{"pid": p["pid"] if not p["free"] else "FREE", "start": p["start"], "end": p["start"] + p["size"], "free": p["free"], "internal_frag": p["internal_frag"]} for p in parts]
            }], time, busy

        frag = partition["size"] - process["size"]
        new_parts = [
            {**p, "pid": process["pid"], "free": False, "internal_frag": frag} if i == idx else p
            for i, p in enumerate(parts)
        ]

        alloc_entry = {"pid": process["pid"], "partition_id": partition["id"], "start": partition["start"], "end": partition["start"] + partition_size, "internal_frag": frag}
        new_tl = tl + [{
            "event": "allocated",
            "pid": process["pid"],
            "size": process["size"],
            "burst_time": process["burst_time"],
            "partition_id": partition["id"],
            "internal_frag": frag,
            "start_time": time,
            "end_time": time + process["burst_time"],
            "memory_map": [{"pid": p["pid"] if not p["free"] else "FREE", "start": p["start"], "end": p["start"] + p["size"], "free": p["free"], "internal_frag": p["internal_frag"]} for p in new_parts]
        }]

        return new_parts, alloc_list + [alloc_entry], fail_list, new_tl, time + process["burst_time"], busy + process["burst_time"]

    parts, allocated, failed, timeline, current_time, cpu_busy = reduce(
        allocate_process, sorted_processes, (partitions, [], [], [], 0, 0)
    )

    def remove_process(acc, process):
        parts, tl, time = acc
        new_parts = [
            {**p, "pid": None, "free": True, "internal_frag": 0} if p["pid"] == process["pid"] else p
            for p in parts
        ]
        new_tl = tl + [{
            "event": "removed",
            "pid": process["pid"],
            "time": time,
            "memory_map": [{"pid": p["pid"] if not p["free"] else "FREE", "start": p["start"], "end": p["start"] + p["size"], "free": p["free"], "internal_frag": p["internal_frag"]} for p in new_parts]
        }]
        return new_parts, new_tl, time

    final_parts, timeline, _ = reduce(remove_process, sorted_processes, (parts, timeline, current_time))

    total_free = sum(p["size"] for p in final_parts if p["free"])
    total_internal_frag = sum(a["internal_frag"] for a in allocated)

    timeline.append({
        "event": "completed",
        "memory_map": [{"pid": p["pid"] if not p["free"] else "FREE", "start": p["start"], "end": p["start"] + p["size"], "free": p["free"], "internal_frag": p["internal_frag"]} for p in final_parts],
        "total_free": total_free,
        "total_used": 0,
        "total_internal_fragmentation": total_internal_frag
    })

    return {
        "strategy": fit_strategy,
        "total_memory": total_memory,
        "partition_size": partition_size,
        "num_partitions": num_partitions,
        "allocated": allocated,
        "failed": [p["pid"] for p in failed],
        "timeline": timeline,
        "avg_burst_time": sum(p["burst_time"] for p in processes) / len(processes),
        "cpu_utilization": (cpu_busy / current_time) * 100 if current_time > 0 else 0,
        "total_internal_fragmentation": total_internal_frag
    }