pages = []
print("Enter page reference string (type 'done' to stop):")
while True:
    page = input("Enter page: ")
    if page.lower() == "done":
        break
    pages.append(int(page))

frames = int(input("Enter number of frames: "))

def lru_pra(pages, frames):
    frame_list = []
    page_faults = 0
    timeline = []
    recent_use = []

    for page in pages:
        fault = False
        if page not in frame_list:
            page_faults += 1
            fault = True
            if len(frame_list) < frames:
                frame_list.append(page)
            else:
                # Remove least recently used
                lru_page = recent_use[0]
                frame_list[frame_list.index(lru_page)] = page
                recent_use.remove(lru_page)

        if page in recent_use:
            recent_use.remove(page)
        recent_use.append(page)

        timeline.append({
            "page": page,
            "frames": frame_list.copy(),
            "fault": fault
        })

    return {
        "algorithm": "LRU",
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

result = lru_pra(pages, frames)
print_pra_result(result)