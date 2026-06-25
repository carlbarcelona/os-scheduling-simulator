def build_disk_result(head, sequence):
    movements = [
        {
            "from_cylinder": sequence[i],
            "to_cylinder": sequence[i + 1],
            "distance": abs(sequence[i + 1] - sequence[i]),
        }
        for i in range(len(sequence) - 1)
    ]
    return {
        "initial_head": head,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": sum(m["distance"] for m in movements),
    }


def clook_disk(head, requests, direction="right", number_of_tracks=0):
    """Circular LOOK: jump back to the farthest request, not the disk boundary."""
    left = sorted(r for r in requests if r < head)
    right = sorted(r for r in requests if r >= head)

    if direction == "left":
        sequence = [head] + list(reversed(left)) + list(reversed(right))
    else:
        sequence = [head] + right + left

    return build_disk_result(head, sequence)
