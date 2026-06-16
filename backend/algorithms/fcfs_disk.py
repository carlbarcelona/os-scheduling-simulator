head = int(input("Enter initial head position: "))
direction = input("Enter direction (left/right): ").lower()
requests = []
print("Enter disk request queue (type 'done' to stop):")
while True:
    r = input("Enter request: ")
    if r.lower() == "done":
        break
    requests.append(int(r))

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

result = fcfs_disk(head, requests, direction)
print(f"\n=== {result['algorithm']} ===")
print(f"Head Movement: {' → '.join(map(str, result['sequence']))}")
print(f"Movements: {', '.join(result['movements'])}")
print(f"Total Head Movement: {result['total_head_movement']}")