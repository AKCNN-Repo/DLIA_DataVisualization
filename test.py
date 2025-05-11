### 
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy.stats import gaussian_kde

from shiny import App, reactive, render, ui
from shinywidgets import render_plotly

# Reactive storage
metrics_data = reactive.Value()
icontrol_data = reactive.Value()
kde_storage = reactive.Value([])

# UI layout
app_ui = ui.page_fluid(
    ui.include_css("styles.css"),
    ui.panel_title("Event Tracking Visualization"),
    ui.layout_sidebar(
        sidebar=ui.sidebar(
            open="desktop",
            ui.input_file("metrics_file", "Upload Event Tracking Metrics CSV"),
            ui.input_file("icontrol_file", "Upload iControl Data CSV"),
            ui.input_select("selected_column", "Select Data Column", choices=[], multiple=False),
            ui.input_slider("time_range", "Select Time Range", min=0, max=100, value=(0, 100), step=1),
            ui.input_slider("smoothing_window", "Smoothing Window Size", min=1, max=100, value=5),
            ui.input_radio_buttons("plot_type", "Select Plot Type", ["Raw", "Smoothed", "Filtered"]),
            ui.input_action_button("update_kde", "Update KDE")
        ),
        main=ui.layout_columns(col_widths=[12])(  # use named argument for layout
            ui.card(full_screen=True)(
                ui.card_header("Time Series with Temperature and Volume"),
                ui.output_plot("time_series_plot")
            ),
            ui.card(full_screen=True)(
                ui.card_header("KDE Distribution of Selected Metric"),
                ui.output_plot("kde_plot")
            )
        )
    )
)

@reactive.effect
@reactive.event(ui.input("metrics_file"))
def load_metrics_file():
    file_info = ui.input("metrics_file")()
    if file_info:
        df = pd.read_csv(file_info[0]["datapath"])
        df["Time"] = pd.to_numeric(df["Time"], errors="coerce").dropna()
        metrics_data.set(df)
        columns = [col for col in df.columns if col != "Time"]
        ui.update_select("selected_column", choices=columns)
        ui.update_slider("time_range", min=int(df["Time"].min()), max=int(df["Time"].max()), value=(int(df["Time"].min()), int(df["Time"].max())))

@reactive.effect
@reactive.event(ui.input("icontrol_file"))
def load_icontrol_file():
    file_info = ui.input("icontrol_file")()
    if file_info:
        df = pd.read_csv(file_info[0]["datapath"])
        df["Time"] = pd.to_numeric(df["Time"], errors="coerce").dropna()
        icontrol_data.set(df)

def smooth_series(series: pd.Series, window_size: int = 5):
    return series.rolling(window=window_size, min_periods=1).mean()

@reactive.calc
def filtered_metrics_data():
    df = metrics_data()
    if df is None:
        return pd.DataFrame()
    tmin, tmax = ui.input("time_range")()
    return df[(df["Time"] >= tmin) & (df["Time"] <= tmax)]

@reactive.calc
def filtered_icontrol_data():
    df = icontrol_data()
    if df is None:
        return pd.DataFrame()
    tmin, tmax = ui.input("time_range")()
    return df[(df["Time"] >= tmin) & (df["Time"] <= tmax)]

@reactive.calc
def processed_column():
    df = filtered_metrics_data()
    col = ui.input("selected_column")()
    if df.empty or col not in df.columns:
        return pd.Series(dtype="float")
    if ui.input("plot_type")() == "Raw":
        return df[col]
    return smooth_series(df[col], ui.input("smoothing_window")())

@reactive.effect
@reactive.event(ui.input("update_kde"))
def update_kde_plot():
    df = filtered_metrics_data()
    col = ui.input("selected_column")()
    if df.empty or col not in df.columns:
        return
    series = df[col].dropna()
    kde = gaussian_kde(series)
    x = np.linspace(series.min() - 0.1, series.max() + 0.1, 100)
    y = kde(x)
    entry = {"x": x, "y": y, "time": ui.input("time_range")(), "column": col}
    storage = kde_storage()
    storage.append(entry)
    kde_storage.set(storage)

@render_plotly
def kde_plot():
    traces = kde_storage()
    col = ui.input("selected_column")()
    fig = go.Figure()
    for trace in traces:
        if trace["column"] == col:
            label = f"{col} @ {trace['time'][0]}–{trace['time'][1]}"
            fig.add_trace(go.Scatter(x=trace["x"], y=trace["y"], mode="lines", name=label))
    fig.update_layout(title="KDE Plot", xaxis_title=col, yaxis_title="Density")
    return fig

@render_plotly
def time_series_plot():
    df_m = filtered_metrics_data()
    df_i = filtered_icontrol_data()
    y_series = processed_column()
    col = ui.input("selected_column")()

    fig = go.Figure()
    if not df_i.empty and "Temperature" in df_i.columns:
        fig.add_trace(go.Scatter(x=df_i["Time"], y=df_i["Temperature"], mode="lines", name="Temperature", yaxis="y2", line=dict(color="orange")))
    if not df_i.empty and "Volume" in df_i.columns:
        fig.add_trace(go.Scatter(x=df_i["Time"], y=df_i["Volume"], mode="lines", name="Volume", yaxis="y2", line=dict(color="green")))
    if not df_m.empty:
        fig.add_trace(go.Scatter(x=df_m["Time"], y=y_series, mode="lines", name=col, line=dict(color="blue")))

    fig.update_layout(
        xaxis=dict(title="Time [hour]"),
        yaxis=dict(title=col, domain=[0, 0.85], titlefont=dict(color="blue"), tickfont=dict(color="blue")),
        yaxis2=dict(title="Temperature / Volume", overlaying="y", side="right", position=0.86, anchor="free", titlefont=dict(color="orange"), tickfont=dict(color="orange")),
        margin=dict(l=50, r=180, t=50, b=50),
        legend=dict(x=1.05, y=1, xanchor="left", yanchor="top")
    )
    return fig

app = App(app_ui, server=None)
