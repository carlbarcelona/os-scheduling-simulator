from functools import reduce


def lru_pra(data):
    pages, frames = data["pages"], data["frames"]

    def process_page(acc, page):
        frame_list, recent, timeline, faults = acc

        # Update recent on EVERY access before any decision
        new_recent = [p for p in recent if p != page] + [page]

        if page in frame_list:
            return frame_list, new_recent, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": None}], faults

        # LRU victim: first page in recency order that is currently in a frame
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
        "page_fault_rate": round(faults / len(pages), 2),
    }
