from functools import reduce


def snapshot(blocks):
    return [
        {"pid": b.get("pid", "FREE"), "start": b["start"], "end": b["start"] + b["size"], "free": b.get("free", True)}
        for b in blocks
    ]


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
        blocks[:idx]
        + [{"start": block["start"], "size": process["size"], "pid": process["pid"], "free": False}]
        + ([{"start": block["start"] + process["size"], "size": remaining, "free": True}] if remaining > 0 else [])
        + blocks[idx + 1:]
    )
    return new_blocks, {"pid": process["pid"], "start": block["start"], "end": block["start"] + process["size"]}, {
        "event": "allocated",
        "pid": process["pid"],
        "size": process["size"],
        "burst_time": process["burst_time"],
        "start_time": current_time,
        "end_time": current_time + process["burst_time"],
        "memory_map": snapshot(new_blocks),
    }


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
        "timeline": timeline,
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

    # Compaction: slide all used blocks together to reclaim fragmented free space
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
        "timeline": timeline,
    }
