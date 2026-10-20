"""Validate saved feature data and the corrected year helper."""
import unittest

import nbformat
import numpy as np
import pandas as pd

from test_capstone import ROOT, cells, run_cells

NOTEBOOK = ROOT / "jupyter-labs-eda-dataviz-v2.ipynb"


class DataVizTests(unittest.TestCase):
    def test_feature_export_preserves_rows_and_encodes_categories(self):
        source = pd.read_csv(ROOT / "dataset_part_2.csv")
        encoded = pd.read_csv(ROOT / "dataset_part_3.csv")
        self.assertEqual(encoded.shape, (90, 80))
        self.assertTrue(encoded.dtypes.eq("float64").all())
        self.assertTrue(np.isfinite(encoded.to_numpy()).all())
        self.assertNotIn("Class", encoded)
        self.assertNotIn("Year", encoded)
        self.assertNotIn("Unnamed: 0", encoded)
        for name in ("FlightNumber", "PayloadMass", "Flights", "GridFins",
                     "Reused", "Legs", "Block", "ReusedCount"):
            np.testing.assert_array_equal(encoded[name], source[name].astype(float))
        for name in ("Orbit", "LaunchSite", "LandingPad", "Serial"):
            columns = [column for column in encoded if column.startswith(name + "_")]
            block = encoded[columns]
            self.assertTrue(block.isin([0.0, 1.0]).all().all())
            np.testing.assert_array_equal(block.sum(axis=1), source[name].notna().astype(float))
            for value in source[name].dropna().unique():
                np.testing.assert_array_equal(encoded[f"{name}_{value}"],
                                              source[name].eq(value).astype(float))

    def test_year_extraction_uses_argument_and_has_no_accumulated_state(self):
        definition = next(s for s in cells(NOTEBOOK) if s.startswith("def Extract_year"))
        ns = run_cells([definition], {"pd": pd})
        dates = pd.Series(["2019-12-31", "2020-01-01"])
        original = dates.copy()
        extract = ns["Extract_year"]
        self.assertEqual(extract(dates).tolist(), [2019, 2020])
        self.assertEqual(extract(dates).tolist(), [2019, 2020])
        self.assertEqual(extract(pd.Series(["2015-06-01"])).tolist(), [2015])
        pd.testing.assert_series_equal(dates, original)
        with self.assertRaises(ValueError):
            extract(pd.Series(["invalid date"]))

    def test_saved_notebook_has_seven_charts_and_no_errors(self):
        notebook = nbformat.read(NOTEBOOK, as_version=4)
        nbformat.validate(notebook)
        outputs = [o for cell in notebook.cells for o in cell.get("outputs", [])]
        self.assertFalse(any(o.output_type == "error" for o in outputs))
        self.assertEqual(sum("image/png" in o.get("data", {}) for o in outputs), 7)
        self.assertEqual(len(list((ROOT / "dataviz_outputs").glob("*.png"))), 7)


if __name__ == "__main__":
    unittest.main()
