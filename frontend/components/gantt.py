
import plotly.figure_factory as ff

def render_gantt(timeline: list, schedule: list) -> "plotly.graph_objs.Figure":
    # Mock data for now
    tasks = [
        dict(Task="P1", Start="2024-01-01", Finish="2024-01-03", Resource="CPU"),
        dict(Task="P2", Start="2024-01-03", Finish="2024-01-06", Resource="CPU"),
        dict(Task="P3", Start="2024-01-06", Finish="2024-01-08", Resource="CPU"),
    ]
    fig = ff.create_gantt(tasks, index_col="Resource", show_colorbar=True)
    return fig
