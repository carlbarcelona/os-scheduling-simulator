from functools import reduce

head = int(input("Enter initial head position: "))
number_of_tracks = int(input("Enter number of tracks: "))
requests = []
print("Enter disk request queue (type 'done' to stop):")
while True:
    r = input("Enter request: ")
    if r.lower() == "done":
        break
    requests.append(int(r))

data = {"head": head, "number_of_tracks": number_of_tracks, "requests": requests}

def build_disk_result(head, sequence):
    movements = [
        {"from_cylinder": sequence[i], "to_cylinder": sequence[i+1], "distance": abs(sequence[i+1] - sequence[i]) if sequence[i] != "?" and sequence[i+1] != "?" else "?"}
        for i in range(len(sequence)-1)
    ]
    return {
        "initial_head": head,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": sum(m["distance"] for m in movements if m["distance"] != "?")
    }

def sstf_disk(data):
    def pick_closest(acc, _):
        seq, remaining = acc
        if not remaining:
            return acc
        closest = min(remaining, key=lambda x: abs(x - seq[-1]))
        return seq + [closest], [r for r in remaining if r != closest]

    sequence, _ = reduce(pick_closest, data["requests"], ([data["head"]], data["requests"]))
    return build_disk_result(data["head"], sequence)

result = sstf_disk(data)
print(f"\n=== SSTF Disk Scheduling ===")
print(f"Initial Head: {result['initial_head']}")
print(f"Sequence: {' → '.join(map(str, result['sequence']))}")
print(f"\n{'From':<12} {'To':<12} {'Distance'}")
print("-" * 35)
for m in result["movements"]:
    print(f"  {str(m['from_cylinder']):<12} {str(m['to_cylinder']):<12} {str(m['distance'])}")
print(f"\nTotal Head Movement: {result['total_head_movement']}")