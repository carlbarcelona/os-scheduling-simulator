from functools import reduce

pages = []
print("Enter page reference string (type 'done' to stop):")
while True:
    page = input("Enter page: ")
    if page.lower() == "done":
        break
    pages.append(int(page))
frames = int(input("Enter number of frames: "))

data = {"pages": pages, "frames": frames}

def mfu_pra(data):
    pages, frames = data["pages"], data["frames"]

    def process_page(acc, page):
        frame_list, freq, timeline, faults = acc
        new_freq = {**freq, page: freq.get(page, 0) + 1}

        if page in frame_list:
            return frame_list, new_freq, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": {p: new_freq[p] for p in frame_list}}], faults

        if len(frame_list) < frames:
            new_frames = frame_list + [page]
        else:
            # Only consider frequencies of pages currently in frame
            victim = max(frame_list, key=lambda p: new_freq.get(p, 0))
            new_frames = [page if p == victim else p for p in frame_list]

        return new_frames, new_freq, timeline + [{"page": page, "frames_state": new_frames.copy(), "fault": True, "frequencies": {p: new_freq[p] for p in new_frames}}], faults + 1

    _, _, timeline, faults = reduce(process_page, pages, ([], {}, [], 0))
    return {
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2)
    }

result = mfu_pra(data)
print(f"\n=== MFU Page Replacement ===")
print(f"Frames: {result['frames']} | Pages: {result['pages']}")
print(f"\n{'Page':<6} {'Frames State':<30} {'Frequencies':<25} {'Fault'}")
print("-" * 75)
for entry in result["timeline"]:
    print(f"  {entry['page']:<6} {str(entry['frames_state']):<30} {str(entry['frequencies']):<25} {'✗ FAULT' if entry['fault'] else '✓ HIT'}")
print(f"\nPage Fault Count: {result['page_fault_count']}")
print(f"Page Fault Rate:  {result['page_fault_rate']}")