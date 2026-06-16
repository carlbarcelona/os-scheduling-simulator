pages = []
print("Enter page reference string (type 'done' to stop):")
while True:
    page = input("Enter page: ")
    if page.lower() == "done":
        break
    pages.append(int(page))

frames = int(input("Enter number of frames: "))

def lfu_pra(pages, frames):
    frame_list = []
    freq = {}
    page_faults = 0
    timeline = []

    for page in pages:
        fault = False
        freq[page] = freq.get(page, 0) + 1

        if page not in frame_list:
            page_faults += 1
            fault = True
            if len(frame_list) < frames:
                frame_list.append(page)
            else:
                # Remove least frequently used
                lfu_page = min(frame_list, key=lambda p: freq[p])
                frame_list[frame_list.index(lfu_page)] = page

        timeline.append({
            "page": page,
            "frames": frame_list.copy(),
            "frequencies": {p: freq[p] for p in frame_list},
            "fault": fault
        })

    return {
        "algorithm": "LFU (Counting Based)",
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": page_faults
    }

def print_pra_result(result):
    print(f"\n=== {result['algorithm']} ===")
    print(f"Frames: {result['frames']} | Page Fault Count: {result['page_fault_count']}")
    print(f"\n{'Page':<6} {'Frames':<30} {'Frequencies':<25} {'Fault'}")
    print("-" * 70)
    for entry in result["timeline"]:
        frames_str = str(entry["frames"])
        freq_str = str(entry.get("frequencies", ""))
        fault_str = "✗ FAULT" if entry["fault"] else "✓"
        print(f"{entry['page']:<6} {frames_str:<30} {freq_str:<25} {fault_str}")

result = lfu_pra(pages, frames)
print_pra_result(result)