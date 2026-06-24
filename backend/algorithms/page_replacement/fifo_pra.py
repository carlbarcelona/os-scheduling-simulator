from functools import reduce


def fifo_pra(data):
    pages, frames = data["pages"], data["frames"]

    def process_page(acc, page):
        frame_list, queue, timeline, faults = acc
        if page in frame_list:
            return frame_list, queue, timeline + [{"page": page, "frames_state": frame_list.copy(), "fault": False, "frequencies": None}], faults

        if len(frame_list) < frames:
            new_frames, new_queue = frame_list + [page], queue + [page]
        else:
            removed = queue[0]
            new_frames = [page if p == removed else p for p in frame_list]
            new_queue = queue[1:] + [page]

        return new_frames, new_queue, timeline + [{"page": page, "frames_state": new_frames.copy(), "fault": True, "frequencies": None}], faults + 1

    _, _, timeline, faults = reduce(process_page, pages, ([], [], [], 0))
    return {
        "frames": frames,
        "pages": pages,
        "timeline": timeline,
        "page_fault_count": faults,
        "page_fault_rate": round(faults / len(pages), 2),
    }
