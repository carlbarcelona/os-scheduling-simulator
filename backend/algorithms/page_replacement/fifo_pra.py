from functools import reduce

pages = []
print("Enter page reference string (type 'done' to stop):")
while True:
    page = input("Enter page: ")
    if page.lower() == "done":
        break
    pages.append(int(page))

frames = int(input("Enter number of frames: "))

def fifo_pra(pages, frames):
    def process_page(acc, page):
        frame_list, queue, schedule, timeline, faults = acc
        if page in frame_list:
            return frame_list, queue, schedule, timeline + [{"type": "hit", "page": page, "frames": frame_list.copy(), "fault": False}], faults

        if len(frame_list) < frames:
            new_frames = frame_list + [page]
            new_queue = queue + [page]
        else:
            removed = queue[0]
            new_frames = [page if p == removed else p for p in frame_list]
            new_queue = queue[1:] + [page]

        new_schedule = schedule + [{"page": page, "fault": True, "frames_after": new_frames.copy()}]
        new_timeline = timeline + [{"type": "fault", "page": page, "frames_before": frame_list.copy(), "frames_after": new_frames.copy()}]
        return new_frames, new_queue, new_schedule, new_timeline, faults + 1

    _, _, schedule, timeline, faults = reduce(process_page, pages, ([], [], [], [], 0))

    return {
        "schedule": schedule,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2)
    }

def print_pra_result(result, algorithm, frames, pages):
    print(f"\n=== {algorithm} Page Replacement ===")
    print(f"Frames: {frames} | Pages: {pages}")
    print(f"\n{'Page':<6} {'Frames Before':<25} {'Frames After':<25} {'Type'}")
    print("-" * 65)
    for entry in result["timeline"]:
        before = str(entry.get("frames_before", entry.get("frames", [])))
        after = str(entry.get("frames_after", entry.get("frames", [])))
        print(f"  {entry['page']:<6} {before:<25} {after:<25} {'✗ FAULT' if entry['type'] == 'fault' else '✓ HIT'}")
    print(f"\nPage Fault Count: {result['page_fault_count']}")
    print(f"Page Fault Rate:  {result['page_fault_rate']}")

result = fifo_pra(pages, frames)
print_pra_result(result, "FIFO", frames, pages)