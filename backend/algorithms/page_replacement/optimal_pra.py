from functools import reduce


def optimal_pra(data):
    pages, frames = data["pages"], data["frames"]

    def find_replace(frame_list, future):
        # Replace the page whose next use is farthest away (or never used again)
        def next_use(p):
            return future.index(p) if p in future else float("inf")
        return max(frame_list, key=next_use)

    def process_page(acc, args):
        i, page = args
        frame_list, timeline, faults = acc
        if page in frame_list:
            return frame_list, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": None}], faults

        future = pages[i + 1:]
        if len(frame_list) < frames:
            new_frames = frame_list + [page]
        else:
            victim = find_replace(frame_list, future)
            new_frames = [page if p == victim else p for p in frame_list]

        return new_frames, timeline + [{"page": page, "frames_state": new_frames.copy(), "fault": True, "frequencies": None}], faults + 1

    _, timeline, faults = reduce(process_page, enumerate(pages), ([], [], 0))
    return {
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2),
    }
