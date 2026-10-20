"""Optional static chart exports for slides; these are not UI screenshots.

Requires Kaleido in addition to the dashboard requirements.
"""

from spacex_dash_app import ROOT, get_pie_chart, get_scatter_chart


def main():
    destination = ROOT / "dashboard_outputs"
    destination.mkdir(exist_ok=True)
    figures = {
        "01_all_sites_success": get_pie_chart("ALL"),
        "02_ccafs_lc40_outcomes": get_pie_chart("CCAFS LC-40"),
        "03_all_sites_payload": get_scatter_chart("ALL", [0, 10000]),
        "04_ksc_filtered_payload": get_scatter_chart("KSC LC-39A", [2000, 6000]),
    }
    for name, figure in figures.items():
        figure.write_html(destination / f"{name}.html", include_plotlyjs=True)
        figure.write_image(destination / f"{name}.png", width=1100, height=500, scale=2)
        print(f"Saved {name}.html and {name}.png")


if __name__ == "__main__":
    main()
