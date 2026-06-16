head = int(input("Enter initial head position: "))
disk_size = int(input("Enter disk size: "))
direction = input("Enter direction (left/right): ").lower()
requests = []
print("Enter disk request queue (type 'done' to stop):")
while True:
    r = input("Enter request: ")
    if r.lower() == "done":
        break
    requests.append(int(r))

def scan_disk(head, disk_size, requests, direction):
    left = sorted([r for r in requests if r < head], reverse=True)
    right = sorted([r for r in requests if r >= head])
    sequence = [head]

    if direction == "left":
        sequence += left + [0] + right
    else:
        sequence += right + [disk_size - 1] + left

    total_movement = sum(abs(sequence[i] - sequence[i-1]) for i in range(1, len(sequence)))
    movements = [f"{sequence[i]}→{sequence[i+1]}" for i in range(len(sequence)-1)]

    return {
        "algorithm": "SCAN Disk Scheduling",
        "initial_head": head,
        "direction": direction,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": total_movement
    }

result = scan_disk(head, disk_size, requests, direction)
print(f"\n=== {result['algorithm']} ===")
print(f"Head Movement: {' → '.join(map(str, result['sequence']))}")
print(f"Movements: {', '.join(result['movements'])}")
print(f"Total Head Movement: {result['total_head_movement']}")