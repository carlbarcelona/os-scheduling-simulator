head = int(input("Enter initial head position: "))
direction = input("Enter direction (left/right): ").lower()
requests = []
print("Enter disk request queue (type 'done' to stop):")
while True:
    r = input("Enter request: ")
    if r.lower() == "done":
        break
    requests.append(int(r))

def build_result(algorithm, head, sequence):
    total = sum(
        abs(sequence[i] - sequence[i+1])
        for i in range(len(sequence)-1)
        if sequence[i] != "?" and sequence[i+1] != "?"
    )
    movements = [
        {"from": sequence[i], "to": sequence[i+1], "distance": abs(sequence[i+1] - sequence[i]) if sequence[i] != "?" and sequence[i+1] != "?" else "?"}
        for i in range(len(sequence)-1)
    ]
    return {
        "algorithm": algorithm,
        "initial_head": head,
        "sequence": sequence,
        "movements": movements,
        "total_head_movement": total
    }

def scan_disk(head, requests, direction):
    left = sorted([r for r in requests if r < head], reverse=True)
    right = sorted([r for r in requests if r >= head])

    if direction == "left":
        # Goes to border (?) on the left, then sweeps right
        sequence = [head] + left + ["?"] + right
    else:
        # Goes to border (?) on the right, then sweeps left
        sequence = [head] + right + ["?"] + left

    return build_result("SCAN", head, sequence)

def print_disk_result(result):
    print(f"\n=== {result['algorithm']} Disk Scheduling ===")
    print(f"Initial Head: {result['initial_head']}")
    print(f"Sequence: {' → '.join(map(str, result['sequence']))}")
    print(f"\n{'From':<10} {'To':<10} {'Distance'}")
    print("-" * 30)
    for m in result["movements"]:
        print(f"  {str(m['from']):<10} {str(m['to']):<10} {str(m['distance'])}")
    print(f"\nTotal Head Movement: {result['total_head_movement']} (excluding border traversal)")

result = scan_disk(head, requests, direction)
print_disk_result(result)