"""SpaceX Dash lab: launch-site pie charts and payload-filtered outcomes.

Run from any directory: python /path/to/capstone/spacex_dash_app.py
The unchanged IBM course dataset is stored locally in data/.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html


ROOT = Path(__file__).resolve().parent
spacex_df = pd.read_csv(ROOT / "data" / "spacex_launch_dash.csv")
min_payload = spacex_df["Payload Mass (kg)"].min()
max_payload = spacex_df["Payload Mass (kg)"].max()
SITES = sorted(spacex_df["Launch Site"].unique())
BOOSTER_ORDER = ["v1.0", "v1.1", "FT", "B4", "B5"]
BOOSTER_COLORS = dict(zip(BOOSTER_ORDER, [
    "#64748b", "#c2410c", "#2563eb", "#7c3aed", "#0f766e",
]))
SITE_COLORS = dict(zip(SITES, ["#2563eb", "#7c3aed", "#0f766e", "#c2410c"]))
OUTCOME_COLORS = {"Failure": "#c2410c", "Success": "#0f766e"}
GRAPH_CONFIG = {"displaylogo": False, "toImageButtonOptions": {"scale": 2}}

app = Dash(__name__, title="SpaceX Launch Records",
           assets_folder=str(ROOT / "assets"))
server = app.server

app.layout = html.Main([
    html.Header([
        html.P("APPLIED DATA SCIENCE CAPSTONE", className="eyebrow"),
        html.H1("SpaceX Launch Records Dashboard"),
        html.P("Explore launch outcomes by site, payload mass, and booster version.",
               className="subtitle"),
        html.Div([
            html.Span(f"{len(spacex_df)} launch records"),
            html.Span(f"{len(SITES)} launch sites"),
            html.Span(f"{int(spacex_df['class'].sum())} successful outcomes"),
        ], className="summary"),
    ]),
    html.Section([
        html.Label("Launch site", htmlFor="site-dropdown", className="control-label"),
        # TASK 1: searchable launch-site dropdown.
        dcc.Dropdown(
            id="site-dropdown",
            options=[{"label": "All Sites", "value": "ALL"}]
                    + [{"label": site, "value": site} for site in SITES],
            value="ALL",
            placeholder="Select a Launch Site here",
            searchable=True,
            clearable=False,
        ),
        html.P("All Sites compares successful outcome counts. Select one site "
               "to compare its successes and failures.", className="hint"),
        dcc.Graph(id="success-pie-chart", config=GRAPH_CONFIG),
    ], className="panel"),
    html.Section([
        html.H2("Payload and launch outcome"),
        html.Label("Payload range (kg)", htmlFor="payload-slider",
                   className="control-label"),
        # TASK 3: 1,000 kg steps, with the full dataset visible by default.
        dcc.RangeSlider(
            id="payload-slider", min=0, max=10000, step=1000,
            marks={n: f"{n:,}" for n in range(0, 10001, 1000)},
            value=[0, 10000], allowCross=False,
            tooltip={"placement": "bottom", "always_visible": False},
        ),
        html.P("The payload range filters the scatter plot only. "
               "Range endpoints are included.", className="hint"),
        dcc.Graph(id="success-payload-scatter-chart", config=GRAPH_CONFIG),
    ], className="panel"),
    html.Footer([
        html.P("Source: IBM course dashboard dataset · 56 historical records. "
               "Success and failure follow the supplied class labels (1 and 0). "
               "Coincident scatter points may overlap."),
        html.P("Use the camera icon on either chart to download a PNG."),
    ]),
], className="dashboard")


def style_figure(fig):
    """Use one readable chart style for every filter selection."""
    fig.update_layout(
        template="plotly_white", font={"family": "Arial, sans-serif", "size": 14},
        margin={"l": 55, "r": 30, "t": 80, "b": 55},
        title={"x": 0.02, "font": {"size": 20}},
        legend_title_text="", paper_bgcolor="white", height=440,
    )
    return fig


# TASK 2: successful launches by site, or success/failure within a site.
@app.callback(Output("success-pie-chart", "figure"),
              Input("site-dropdown", "value"))
def get_pie_chart(entered_site):
    if entered_site == "ALL":
        counts = (spacex_df.groupby("Launch Site", as_index=False)["class"]
                  .sum().rename(columns={"class": "Count"}))
        fig = px.pie(
            counts, names="Launch Site", values="Count", color="Launch Site",
            color_discrete_map=SITE_COLORS,
            title="Successful outcomes by launch site",
        )
    else:
        selected = spacex_df.loc[spacex_df["Launch Site"].eq(entered_site)]
        counts = selected["class"].value_counts().reindex([0, 1], fill_value=0)
        fig = px.pie(
            names=["Failure", "Success"], values=counts.to_numpy(),
            color=["Failure", "Success"], color_discrete_map=OUTCOME_COLORS,
            title=f"Launch outcomes · {entered_site}",
        )
    fig.update_traces(
        textinfo="percent+value", sort=False,
        hovertemplate="%{label}<br>Launches: %{value}<br>Share: %{percent}<extra></extra>",
    )
    return style_figure(fig)


# TASK 4: both site and inclusive payload limits filter the scatter plot.
@app.callback(Output("success-payload-scatter-chart", "figure"),
              Input("site-dropdown", "value"),
              Input("payload-slider", "value"))
def get_scatter_chart(entered_site, payload_range):
    low, high = payload_range
    selected = spacex_df.loc[
        spacex_df["Payload Mass (kg)"].between(low, high, inclusive="both")
    ]
    if entered_site != "ALL":
        selected = selected.loc[selected["Launch Site"].eq(entered_site)]
    label = "All sites" if entered_site == "ALL" else entered_site
    fig = px.scatter(
        selected, x="Payload Mass (kg)", y="class",
        color="Booster Version Category",
        category_orders={"Booster Version Category": BOOSTER_ORDER},
        color_discrete_map=BOOSTER_COLORS,
        hover_data=["Flight Number", "Launch Site", "Booster Version"],
        labels={"class": "Launch outcome"},
        title=f"{label} · {low:,.0f}–{high:,.0f} kg · {len(selected)} records",
    )
    fig.update_traces(marker={"size": 11, "opacity": 0.8,
                              "line": {"width": 1, "color": "white"}})
    fig.update_yaxes(tickvals=[0, 1], ticktext=["Failure (0)", "Success (1)"],
                     range=[-0.15, 1.15], fixedrange=True)
    fig.update_xaxes(range=[0, 10000], tickformat=",")
    if selected.empty:
        fig.add_annotation(
            text="No launches match this site and payload range.",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        )
    return style_figure(fig)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8050,
                        help="Local port (default: 8050)")
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port, debug=False)
