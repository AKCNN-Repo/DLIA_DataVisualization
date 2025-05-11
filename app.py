### vis
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy.stats import gaussian_kde

from shiny import App, reactive, render
from shiny.express import input, ui
from shinywidgets import render_plotly

# Reactive storage
metrics_data = reactive.Value()
icontrol_data = reactive.Value()
kde_storage = reactive.Value([])

# # Page layout and sidebar
ui.page_opts(title="Event Tracking Visualization", fillable=True)
ui.include_css("styles.css")

# app_ui = ui.page_fluid(
#     ui.include_css("styles.css"),
#     ui.panel_title("Event Tracking Visualization"),
#     # all your layout columns/cards go here
# )


with ui.sidebar(open="desktop"):
    ui.input_file("metrics_file", "Upload Event Tracking Metrics CSV")
    ui.input_file("icontrol_file", "Upload iControl Data CSV")
    ui.input_select("selected_column", "Select Data Column", choices=[], multiple=False)
    ui.input_slider("time_range", "Select Time Range", min=0, max=100, value=(0, 100), step=1)
    ui.input_slider("smoothing_window", "Smoothing Window Size", min=1, max=100, value=5)
    ui.input_radio_buttons("plot_type", "Select Plot Type", ["Raw", "Smoothed", "Filtered"])
    ui.input_action_button("update_kde", "Update KDE")

# Load Metrics CSV and update UI
@reactive.effect
@reactive.event(input.metrics_file)
def load_metrics_file():
    file_info = input.metrics_file()
    if file_info is not None:
        df = pd.read_csv(file_info[0]["datapath"])
        df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
        df = df.dropna(subset=["Time"])
        metrics_data.set(df)

        metric_cols = [col for col in df.columns if col != "Time"]
        ui.update_select("selected_column", choices=metric_cols)

        tmin = int(df["Time"].min())
        tmax = int(df["Time"].max())
        ui.update_slider("time_range", min=tmin, max=tmax, value=(tmin, tmax))

# Load iControl CSV
@reactive.effect
@reactive.event(input.icontrol_file)
def load_icontrol_file():
    file_info = input.icontrol_file()
    if file_info is not None:
        df = pd.read_csv(file_info[0]["datapath"])
        df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
        df = df.dropna(subset=["Time"])
        icontrol_data.set(df)

# Smoothing function
def smooth_series(series: pd.Series, window_size: int = 5):
    return series.rolling(window=window_size, min_periods=1).mean()

# Reactive filtered datasets
@reactive.calc
def filtered_metrics_data():
    df = metrics_data()
    if df is None:
        return pd.DataFrame()
    tmin, tmax = input.time_range()
    return df[(df["Time"] >= tmin) & (df["Time"] <= tmax)]

@reactive.calc
def filtered_icontrol_data():
    df = icontrol_data()
    if df is None:
        return pd.DataFrame()
    tmin, tmax = input.time_range()
    return df[(df["Time"] >= tmin) & (df["Time"] <= tmax)]

@reactive.calc
def processed_column():
    df = filtered_metrics_data()
    col = input.selected_column()
    if df.empty or col not in df.columns:
        return pd.Series(dtype="float")
    if input.plot_type() == "Raw":
        return df[col]
    else:
        return smooth_series(df[col], input.smoothing_window())

# Add KDE trace when button is clicked
@reactive.effect
@reactive.event(input.update_kde)
def update_kde_plot():
    df = filtered_metrics_data()
    col = input.selected_column()
    if df.empty or col not in df.columns:
        return
    series = df[col].dropna()
    if series.empty:
        return
    kde = gaussian_kde(series)
    x_min, x_max = series.min(), series.max()
    x_vals = np.linspace(x_min - 0.1*(x_max - x_min), x_max + 0.1*(x_max - x_min), 100)
    y_vals = kde(x_vals)
    trace = {"x": x_vals, "y": y_vals, "time": input.time_range(), "column": col}
    kde_traces = kde_storage()
    kde_traces.append(trace)
    kde_storage.set(kde_traces)

# # KDE Plot
# @render_plotly
# def kde_plot():
#     fig = go.Figure()
#     col = input.selected_column()
#     for trace in kde_storage():
#         if trace["column"] == col:
#             label = f"{col} @ Time {trace['time'][0]}–{trace['time'][1]}"
#             fig.add_trace(go.Scatter(x=trace["x"], y=trace["y"], mode="lines", name=label))
#     fig.update_layout(
#         xaxis_title=col,
#         yaxis_title="Density",
#         title="KDE Distribution",
#         margin=dict(l=40, r=40, t=40, b=40),
#     )
#     return fig

# # Time Series Plot
# @render_plotly
# def time_series_plot():
#     df_m = filtered_metrics_data()
#     df_i = filtered_icontrol_data()
#     y_series = processed_column()
#     col = input.selected_column()

#     fig = go.Figure()

#     if not df_i.empty and "Temperature" in df_i.columns:
#         fig.add_trace(go.Scatter(x=df_i["Time"], y=df_i["Temperature"], mode="lines", name="Temperature", yaxis="y2", line=dict(color="orange")))

#     if not df_i.empty and "Volume" in df_i.columns:
#         fig.add_trace(go.Scatter(x=df_i["Time"], y=df_i["Volume"], mode="lines", name="Volume", yaxis="y2", line=dict(color="green")))

#     if not df_m.empty and col in df_m.columns:
#         fig.add_trace(go.Scatter(x=df_m["Time"], y=y_series, mode="lines", name=f"{input.plot_type()} {col}", line=dict(color="blue")))

#     fig.update_layout(
#         xaxis=dict(title="Time [hour]"),
#         yaxis=dict(title=col, titlefont=dict(color="blue"), tickfont=dict(color="blue"), domain=[0, 0.85]),
#         yaxis2=dict(title="Temperature / Volume", titlefont=dict(color="orange"), tickfont=dict(color="orange"), overlaying="y", side="right", anchor="free", position=0.86),
#         legend=dict(x=1.05, y=1, xanchor="left", yanchor="top", bgcolor="#E2E2E2", bordercolor="#FFFFFF", borderwidth=2),
#         margin=dict(l=50, r=180, t=50, b=50)
#     )
#     return fig

# Layout (Express style)
with ui.layout_columns(col_widths=[12]):
    with ui.card(full_screen=True):
        ui.card_header("Time Series with Temperature and Volume")

        @render_plotly
        def time_series_plot():
            df_m = filtered_metrics_data()
            df_i = filtered_icontrol_data()
            y_series = processed_column()
            col = input.selected_column()

            fig = go.Figure()
            if not df_i.empty and "Temperature" in df_i.columns:
                fig.add_trace(go.Scatter(
                    x=df_i["Time"], y=df_i["Temperature"],
                    mode="lines", name="Temperature",
                    yaxis="y2", line=dict(color="orange")
                ))
            if not df_i.empty and "Volume" in df_i.columns:
                fig.add_trace(go.Scatter(
                    x=df_i["Time"], y=df_i["Volume"],
                    mode="lines", name="Volume",
                    yaxis="y2", line=dict(color="green")
                ))
            if not df_m.empty and col in df_m.columns:
                fig.add_trace(go.Scatter(
                    x=df_m["Time"], y=y_series,
                    mode="lines", name=f"{input.plot_type()} {col}",
                    line=dict(color="blue")
                ))
            fig.update_layout(
                xaxis_title="Time [hour]",
                yaxis=dict(
                    title=col,
                    domain=[0, 0.85],
                    titlefont=dict(color="blue"),
                    tickfont=dict(color="blue")
                ),
                yaxis2=dict(
                    title="Temperature / Volume",
                    overlaying="y",
                    side="right",
                    position=0.86,
                    anchor="free",
                    titlefont=dict(color="orange"),
                    tickfont=dict(color="orange")
                ),
                margin=dict(l=50, r=180, t=50, b=50),
                legend=dict(x=1.05, y=1, xanchor="left", yanchor="top")
            )
            return fig

    with ui.card(full_screen=True):
        ui.card_header("KDE Distribution of Selected Metric")

        @render_plotly
        def kde_plot():
            traces = kde_storage()
            col = input.selected_column()
            fig = go.Figure()
            for trace in traces:
                if trace["column"] == col:
                    label = f"{col} @ Time {trace['time'][0]}–{trace['time'][1]}"
                    fig.add_trace(go.Scatter(
                        x=trace["x"], y=trace["y"],
                        mode="lines", name=label
                    ))
            fig.update_layout(
                title="KDE Distribution",
                xaxis_title=col,
                yaxis_title="Density",
                margin=dict(l=40, r=40, t=40, b=40)
            )
            return fig



# App declaration
app = App(ui.page(), server=None)
