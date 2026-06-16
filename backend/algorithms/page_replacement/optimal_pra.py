pages = []
print("Enter page reference string (type 'done' to stop):")
while True:
    page = input("Enter page: ")
    if page.lower() == "done":
        break
    pages.append(int(page))

frames = int(input("Enter number of frames: "))

def optimal_pra(pages, frames):
    frame_list = []
    page_faults = 0
    timeline = []

    for i, page in enumerate(pages):
        fault = False
        if page not in frame_list:
            page_faults += 1
            fault = True
            if len(frame_list) < frames:
                frame_list.append(page)
            else:
                # Find page used farthest in the future
                future = pages[i + 1:]
                farthest = -1
                replace = frame_list[0]
                for f in frame_list:
                    if f not in future:
                        replace = f
                        break
                    idx = future.index(f)
                    if idx > farthest:
                        farthest = idx
                        replace = f
                frame_list[frame_list.index(replace)] = page

        timeline.append({
            "page": page,
            "frames": frame_list.copy(),
            "fault": fault
        })

    return {
        "algorithm": "Optimal",
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": page_faults
    }

def print_pra_result(result):
    print(f"\n=== {result['algorithm']} ===")
    print(f"Frames: {result['frames']} | Page Fault Count: {result['page_fault_count']}")
    print(f"\n{'Page':<6} {'Frames':<30} {'Fault'}")
    print("-" * 45)
    for entry in result["timeline"]:
        frames_str = str(entry["frames"])
        fault_str = "✗ FAULT" if entry["fault"] else "✓"
        print(f"{entry['page']:<6} {frames_str:<30} {fault_str}")

result = optimal_pra(pages, frames)
print_pra_result(result)