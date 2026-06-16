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

def lru_pra(data):
    pages, frames = data["pages"], data["frames"]

    def process_page(acc, page):
        frame_list, recent, timeline, faults = acc

        # Update recent on EVERY access before any decision
        new_recent = [p for p in recent if p != page] + [page]

        if page in frame_list:
            return frame_list, new_recent, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": None}], faults

        # LRU victim: scan new_recent left to right, first one found IN frame is the LRU
        # new_recent[0] is least recently used overall, but must be in frame
        lru_victim = next(p for p in new_recent if p in frame_list) if len(frame_list) == frames else None

        if lru_victim is None:
            new_frames = frame_list + [page]
        else:
            new_frames = [page if p == lru_victim else p for p in frame_list]

        return new_frames, new_recent, timeline + [{"page": page, "frames_state": new_frames.copy(), "fault": True, "frequencies": None}], faults + 1

    _, _, timeline, faults = reduce(process_page, pages, ([], [], [], 0))
    return {
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2)
    }

result = lru_pra(data)
print(f"\n=== LRU Page Replacement ===")
print(f"Frames: {result['frames']} | Pages: {result['pages']}")
print(f"\n{'Page':<6} {'Frames State':<30} {'Fault'}")
print("-" * 50)
for entry in result["timeline"]:
    print(f"  {entry['page']:<6} {str(entry['frames_state']):<30} {'✗ FAULT' if entry['fault'] else '✓ HIT'}")
print(f"\nPage Fault Count: {result['page_fault_count']}")
print(f"Page Fault Rate:  {result['page_fault_rate']}")