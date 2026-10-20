"""Check Folium launch markers, repeatable layers, and geographic calculations."""
from math import pi
from pathlib import Path
import shutil
import tempfile
import unittest

import folium
import nbformat
import pandas as pd

from prepare_launch_site_points import closest_point
from test_capstone import ROOT, cells, run_cells, working_directory

NOTEBOOK = ROOT / "lab-jupyter-launch-site-location-v2.ipynb"


class LocationTests(unittest.TestCase):
    def test_actual_notebook_markers_distances_and_reruns(self):
        nbformat.validate(nbformat.read(NOTEBOOK, as_version=4))
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            shutil.copytree(ROOT / "data", "data")
            sources = cells(NOTEBOOK)
            ns = run_cells(sources)
            self.assertEqual(len(ns["launch_sites_df"]), 4)
            self.assertEqual(len(ns["spacex_df"]), 56)
            self.assertEqual(ns["site_summary"]["Successes"].sum(), 24)
            cluster = ns["marker_cluster"]
            markers = [child for child in cluster._children.values()
                       if isinstance(child, folium.Marker)]
            self.assertEqual(len(markers), 56)
            self.assertEqual(len({id(marker) for marker in markers}), 56)
            for marker, (_, record) in zip(markers, ns["spacex_df"].iterrows()):
                self.assertIsInstance(marker, folium.Marker)
                self.assertEqual(marker.location, [record["Lat"], record["Long"]])
                self.assertEqual(marker.icon.options["marker_color"], record["marker_color"])
            repeat = next(s for s in sources if s.startswith("# Rebuild on rerun"))
            run_cells([repeat], ns)
            self.assertEqual(sum(isinstance(child, folium.Marker)
                                 for child in ns["marker_cluster"]._children.values()), 56)
            self.assertEqual(len(list(Path("location_outputs").glob("*.html"))), 3)
            distances = pd.read_csv("location_outputs/launch_site_distances.csv").set_index("Feature")
            self.assertEqual(set(distances.index), {"Coastline", "Railway", "Major road", "City/town centre"})
            self.assertAlmostEqual(distances.loc["Coastline", "Distance_km"], 0.922, places=3)
            self.assertAlmostEqual(distances.loc["Major road", "Distance_km"], 6.385, places=3)
            self.assertAlmostEqual(distances.loc["City/town centre", "Distance_km"], 19.568, places=3)
            self.assertEqual(distances.loc["Railway", "Name"], "Rail spur")
            with self.assertRaises(ValueError):
                ns["assign_marker_color"](2)

    def test_haversine_zero_symmetry_antipodes_and_invalid_coordinates(self):
        source = next(s for s in cells(NOTEBOOK) if "def calculate_distance(" in s)
        ns = run_cells([source])
        distance = ns["calculate_distance"]
        self.assertEqual(distance(28, -80, 28, -80), 0)
        self.assertAlmostEqual(distance(0, 0, 0, 90), 6373 * pi / 2)
        self.assertAlmostEqual(distance(0, 0, 0, 180), 6373 * pi)
        self.assertAlmostEqual(distance(28, -80, 34, -120), distance(34, -120, 28, -80))
        for args in ((91, 0, 0, 0), (0, 181, 0, 0), (float("nan"), 0, 0, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                distance(*args)

    def test_nearest_line_point_is_not_limited_to_vertices(self):
        result = closest_point((0, 0), [{"lat": -1, "lon": 1}, {"lat": 1, "lon": 1}])
        self.assertEqual(result, (0, 1))
        endpoint = closest_point((2, 0), [{"lat": -1, "lon": 1}, {"lat": 1, "lon": 1}])
        self.assertAlmostEqual(endpoint[0], 1)
        self.assertAlmostEqual(endpoint[1], 1)
        with self.assertRaises(ValueError):
            closest_point((0, 0), [])


if __name__ == "__main__":
    unittest.main()
