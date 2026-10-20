"""Check the assignment's aggregation and filtering through Dash callbacks."""

import unittest

import pandas as pd

from spacex_dash_app import SITES, app, spacex_df


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.client = app.server.test_client()

    def callback(self, component, site, payload=None):
        inputs = [{"id": "site-dropdown", "property": "value", "value": site}]
        if payload is not None:
            inputs.append({"id": "payload-slider", "property": "value", "value": payload})
        response = self.client.post("/_dash-update-component", json={
            "output": f"{component}.figure",
            "outputs": {"id": component, "property": "figure"},
            "inputs": inputs, "state": [],
            "changedPropIds": [f"{inputs[-1]['id']}.value"],
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["response"][component]["figure"]

    def test_page_layout_and_callback_dependencies(self):
        for path in ["/", "/_dash-layout", "/_dash-dependencies", "/assets/dashboard.css"]:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
        dependencies = self.client.get("/_dash-dependencies").get_json()
        self.assertEqual(len(dependencies), 2)

    def test_pie_counts_for_all_and_each_site(self):
        trace = self.callback("success-pie-chart", "ALL")["data"][0]
        self.assertEqual(dict(zip(trace["labels"], trace["values"])), {
            "CCAFS LC-40": 7, "CCAFS SLC-40": 3, "KSC LC-39A": 10, "VAFB SLC-4E": 4,
        })
        expected = {
            "CCAFS LC-40": (19, 7), "CCAFS SLC-40": (4, 3),
            "KSC LC-39A": (3, 10), "VAFB SLC-4E": (6, 4),
        }
        for site, (failure, success) in expected.items():
            trace = self.callback("success-pie-chart", site)["data"][0]
            self.assertEqual(dict(zip(trace["labels"], trace["values"])),
                             {"Failure": failure, "Success": success})

    def test_scatter_filters_points_and_preserves_data(self):
        original = spacex_df.copy(deep=True)
        for site in ["ALL"] + SITES:
            for limits in [[0, 10000], [2000, 5000], [0, 0], [9600, 9600], [7000, 8000]]:
                with self.subTest(site=site, limits=limits):
                    fig = self.callback("success-payload-scatter-chart", site, limits)
                    expected = spacex_df.loc[spacex_df["Payload Mass (kg)"]
                                             .between(*limits)]
                    if site != "ALL":
                        expected = expected.loc[expected["Launch Site"].eq(site)]
                    actual = []
                    for trace in fig["data"]:
                        for mass, outcome, custom in zip(
                            trace["x"], trace["y"], trace["customdata"]
                        ):
                            actual.append((custom[0], mass, outcome, trace["name"]))
                    wanted = list(expected[["Flight Number", "Payload Mass (kg)",
                                            "class", "Booster Version Category"]]
                                  .itertuples(index=False, name=None))
                    self.assertCountEqual(actual, wanted)
                    if expected.empty:
                        self.assertIn("No launches", fig["layout"]["annotations"][0]["text"])
        pd.testing.assert_frame_equal(spacex_df, original)


if __name__ == "__main__":
    unittest.main()
