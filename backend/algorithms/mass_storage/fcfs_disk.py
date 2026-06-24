def fcfs_disk(head, requests, direction):
    sequence = [head] + requests
    total_movement = sum(abs(sequence[i] - sequence[i-1]) for i in range(1, len(sequence)))
    movements = [f"{sequence[i]}→{sequence[i+1]}" for i in range(len(sequence)-1)]

    return {
        "algorithm": "FCFS Disk Scheduling",
        "initial_head": head,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": total_movement
    }