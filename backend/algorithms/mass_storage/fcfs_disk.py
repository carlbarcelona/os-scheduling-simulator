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


def fcfs_disk(head, requests, direction="right", number_of_tracks=0):
    """Serve requests in the order they arrive."""
    sequence = [head] + list(requests)
    return build_disk_result(head, sequence)
