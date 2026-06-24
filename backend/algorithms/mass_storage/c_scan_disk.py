def cscan_disk(head, disk_size, requests, direction):
    left = sorted([r for r in requests if r < head], reverse=True)
    right = sorted([r for r in requests if r >= head])
    sequence = [head]

    if direction == "right":
        sequence += right + [disk_size - 1, 0] + sorted(left)
    else:
        sequence += left + [0, disk_size - 1] + sorted(right, reverse=True)

    total_movement = sum(abs(sequence[i] - sequence[i-1]) for i in range(1, len(sequence)))
    movements = [f"{sequence[i]}→{sequence[i+1]}" for i in range(len(sequence)-1)]

    return {
        "algorithm": "C-SCAN Disk Scheduling",
        "initial_head": head,
        "direction": direction,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": total_movement
    }