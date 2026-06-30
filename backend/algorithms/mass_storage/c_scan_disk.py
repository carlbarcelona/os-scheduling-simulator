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


def cscan_disk(head, requests, direction="right", number_of_tracks=0):
    """Circular SCAN: sweep to one boundary, jump to the other, continue."""
    left = sorted(r for r in requests if r < head)
    right = sorted(r for r in requests if r >= head)

    if direction == "left":
        # down to 0, jump to last track, continue down
        sequence = [head] + list(reversed(left)) + [0, number_of_tracks - 1] + list(reversed(right))
    else:
        # up to last track, jump to 0, continue up
        sequence = [head] + right + [number_of_tracks - 1, 0] + left

    return build_disk_result(head, sequence)
