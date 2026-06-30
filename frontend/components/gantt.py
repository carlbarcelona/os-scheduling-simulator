# frontend/components/gantt.py
"""CPU-scheduling Gantt chart built from the backend `timeline`.

The backend returns `timeline` as ordered execution blocks:
    {"type": "process"|"idle", "pid": str|None, "start": int, "end": int}
and `schedule` as per-process run spans. We render with plotly graph_objects
(not figure_factory.create_gantt, which needs datetimes) so integer CPU time
units map directly. Two layouts are supported:

    layout="single"      one CPU lane, blocks left-to-right; idle shown grey.
    layout="per_process" one row per process; Round-Robin slices share a row;
                         idle omitted (gaps imply idle).
"""

import plotly.graph_objects as go

# Distinct, high-contrast palette (neon-ish, matching the app's other charts).
_PALETTE = [
    "#00ff9d", "#4d9dff", "#ff6e6e", "#ffd166", "#b083ff",
    "#06d6a0", "#ef476f", "#ffa552", "#5ad1e0", "#c77dff",
]
_IDLE_COLOR = "#3a3f4b"


def _color_map(timeline):
    """Stable pid -> color in first-appearance order."""
    pids = []
    for b in timeline:
        pid = b.get("pid")
        if b.get("type") != "idle" and pid and pid not in pids:
            pids.append(pid)
    return {pid: _PALETTE[i % len(_PALETTE)] for i, pid in enumerate(pids)}


def _empty_fig(msg="No timeline to display — run a simulation first."):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14))
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=200, margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


def render_gantt(timeline, schedule=None, layout="single"):
    """Build a Gantt figure from a CPU-scheduling `timeline` (see module docstring)."""
    if not timeline:
        return _empty_fig()

    colors = _color_map(timeline)
    fig = go.Figure()
    seen = set()  # de-duplicate legend entries

    if layout == "per_process":
        order = list(colors.keys())
        for b in timeline:
            if b.get("type") == "idle" or not b.get("pid"):
                continue
            pid, start, end = b["pid"], b["start"], b["end"]
            fig.add_trace(go.Bar(
                y=[pid], x=[end - start], base=start, orientation="h",
                marker_color=colors[pid],
                marker_line_color="rgba(0,0,0,0.45)", marker_line_width=1,
                name=pid, legendgroup=pid, showlegend=pid not in seen,
                hovertemplate=f"{pid}: {start}–{end} (dur {end - start})<extra></extra>",
            ))
            seen.add(pid)
        # First-appearing process at the top.
        fig.update_yaxes(
            categoryorder="array", categoryarray=list(reversed(order)), title="Process"
        )
        height = max(220, 56 * len(colors))
    else:  # single CPU lane
        for b in timeline:
            is_idle = b.get("type") == "idle" or not b.get("pid")
            label = "Idle" if is_idle else b["pid"]
            start, end = b["start"], b["end"]
            dur = end - start
            color = _IDLE_COLOR if is_idle else colors.get(b["pid"], _PALETTE[0])
            fig.add_trace(go.Bar(
                y=["CPU"], x=[dur], base=start, orientation="h",
                marker_color=color,
                marker_line_color="rgba(0,0,0,0.45)", marker_line_width=1,
                text=[label], textposition="inside", insidetextanchor="middle",
                textfont=dict(color="#0b0e14" if not is_idle else "#c9d1d9"),
                name=label, legendgroup=label, showlegend=label not in seen,
                hovertemplate=f"{label}: {start}–{end} (dur {dur})<extra></extra>",
            ))
            seen.add(label)
        fig.update_yaxes(showticklabels=False, title="")
        height = 260

    max_t = max(b["end"] for b in timeline)
    fig.update_xaxes(title="Time", rangemode="tozero", dtick=1 if max_t <= 30 else None)
    fig.update_layout(
        barmode="overlay",
        bargap=0.3,
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig
