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


def look_disk(head, requests, direction="right", number_of_tracks=0):
    """Like SCAN but only travels as far as the last request (no boundary)."""
    left = sorted(r for r in requests if r < head)
    right = sorted(r for r in requests if r >= head)

    if direction == "left":
        sequence = [head] + list(reversed(left)) + right
    else:
        sequence = [head] + right + list(reversed(left))

    return build_disk_result(head, sequence)
