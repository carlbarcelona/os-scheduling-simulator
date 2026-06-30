from functools import reduce


def lfu_pra(data):
    pages, frames = data["pages"], data["frames"]

    def process_page(acc, page):
        frame_list, freq, timeline, faults = acc
        new_freq = {**freq, page: freq.get(page, 0) + 1}

        if page in frame_list:
            return frame_list, new_freq, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": {p: new_freq[p] for p in frame_list}}], faults

        if len(frame_list) < frames:
            new_frames = frame_list + [page]
        else:
            # Evict the least frequently used page currently in a frame
            victim = min(frame_list, key=lambda p: new_freq.get(p, 0))
            new_frames = [page if p == victim else p for p in frame_list]

        return new_frames, new_freq, timeline + [{"page": page, "frames_state": new_frames.copy(), "fault": True, "frequencies": {p: new_freq[p] for p in new_frames}}], faults + 1

    _, _, timeline, faults = reduce(process_page, pages, ([], {}, [], 0))
    return {
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2),
    }
