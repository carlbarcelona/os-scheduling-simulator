

def clook_disk(head, requests, direction):
    left = sorted([r for r in requests if r < head], reverse=True)
    right = sorted([r for r in requests if r >= head])
    sequence = [head]

    # C-LOOK jumps back to the smallest/largest request, not disk end
    if direction == "right":
        sequence += right + sorted(left)
    else:
        sequence += left + sorted(right, reverse=True)

    total_movement = sum(abs(sequence[i] - sequence[i-1]) for i in range(1, len(sequence)))
    movements = [f"{sequence[i]}→{sequence[i+1]}" for i in range(len(sequence)-1)]

    return {
        "algorithm": "C-LOOK Disk Scheduling",
        "initial_head": head,
        "direction": direction,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": total_movement
    }

