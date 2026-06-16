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

def lru_approximation_pra(data):
    pages, frames = data["pages"], data["frames"]

    def give_second_chance(frame_list, ref_bits, queue, new_page):
        candidate = queue[0]
        if ref_bits.get(candidate, 0) == 0:
            new_frames = [new_page if p == candidate else p for p in frame_list]
            new_bits = {k: v for k, v in ref_bits.items() if k != candidate}
            new_bits[new_page] = 1
            return new_frames, new_bits, queue[1:] + [new_page]
        return give_second_chance(frame_list, {**ref_bits, candidate: 0}, queue[1:] + [candidate], new_page)

    def process_page(acc, page):
        frame_list, ref_bits, queue, timeline, faults = acc
        if page in frame_list:
            new_bits = {**ref_bits, page: 1}
            return frame_list, new_bits, queue, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": new_bits}], faults

        if len(frame_list) < frames:
            new_frames = frame_list + [page]
            new_bits = {**ref_bits, page: 1}
            new_queue = queue + [page]
        else:
            new_frames, new_bits, new_queue = give_second_chance(frame_list, ref_bits, queue, page)

        return new_frames, new_bits, new_queue, timeline + [{"page": page, "frames_state": new_frames.copy(), "fault": True, "frequencies": new_bits.copy()}], faults + 1

    _, _, _, timeline, faults = reduce(process_page, pages, ([], {}, [], [], 0))
    return {
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2)
    }

result = lru_approximation_pra(data)
print(f"\n=== LRU Approximation Page Replacement ===")
print(f"Frames: {result['frames']} | Pages: {result['pages']}")
print(f"\n{'Page':<6} {'Frames State':<30} {'Ref Bits':<25} {'Fault'}")
print("-" * 70)
for entry in result["timeline"]:
    print(f"  {entry['page']:<6} {str(entry['frames_state']):<30} {str(entry['frequencies']):<25} {'✗ FAULT' if entry['fault'] else '✓ HIT'}")
print(f"\nPage Fault Count: {result['page_fault_count']}")
print(f"Page Fault Rate:  {result['page_fault_rate']}")