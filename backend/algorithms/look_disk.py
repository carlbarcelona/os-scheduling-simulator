head = int(input("Enter initial head position: "))
number_of_tracks = int(input("Enter number of tracks: "))
direction = input("Enter direction (left/right): ").lower()
requests = []
print("Enter disk request queue (type 'done' to stop):")
while True:
    r = input("Enter request: ")
    if r.lower() == "done":
        break
    requests.append(int(r))

data = {"head": head, "number_of_tracks": number_of_tracks, "requests": requests, "direction": direction}

def build_disk_result(head, sequence):
    movements = [
        {"from_cylinder": sequence[i], "to_cylinder": sequence[i+1], "distance": abs(sequence[i+1] - sequence[i])}
        for i in range(len(sequence)-1)
    ]
    return {
        "initial_head": head,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": sum(m["distance"] for m in movements)
    }

def look_disk(data):
    head, requests, direction = data["head"], data["requests"], data["direction"]
    left = sorted([r for r in requests if r < head], reverse=True)
    right = sorted([r for r in requests if r >= head])
    sequence = [head] + (left + right if direction == "left" else right + left)
    return build_disk_result(head, sequence)

result = look_disk(data)
print(f"\n=== LOOK Disk Scheduling ===")
print(f"Initial Head: {result['initial_head']}")
print(f"Sequence: {' → '.join(map(str, result['sequence']))}")
print(f"\n{'From':<12} {'To':<12} {'Distance'}")
print("-" * 35)
for m in result["movements"]:
    print(f"  {str(m['from_cylinder']):<12} {str(m['to_cylinder']):<12} {str(m['distance'])}")
print(f"\nTotal Head Movement: {result['total_head_movement']}")