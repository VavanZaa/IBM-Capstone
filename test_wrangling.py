"""Check the lab's counts, outcome labels, and CSV export."""
from pathlib import Path
import shutil
import tempfile
import unittest

import nbformat
import pandas as pd

from test_capstone import ROOT, cells, run_cells, working_directory

NOTEBOOK = ROOT / "labs-jupyter-spacex-Data wrangling-v2.ipynb"


class WranglingTests(unittest.TestCase):
    def test_real_dataset_export_and_course_reference_fallback(self):
        nbformat.validate(nbformat.read(NOTEBOOK, as_version=4))
        reference = ROOT / "data/course_dataset_part_1_reference.csv"
        for use_previous_lab in (True, False):
            with self.subTest(use_previous_lab=use_previous_lab):
                with tempfile.TemporaryDirectory() as directory, working_directory(directory):
                    if use_previous_lab:
                        shutil.copyfile(ROOT / "dataset_part_1.csv", "dataset_part_1.csv")
                    else:
                        Path("data").mkdir()
                        shutil.copyfile(reference, Path("data") / reference.name)
                    ns = run_cells(cells(NOTEBOOK))
                    result = pd.read_csv("dataset_part_2.csv")
                    self.assertEqual(result.shape, (90, 18))
                    self.assertEqual(result.Class.value_counts().to_dict(), {1: 60, 0: 30})
                    self.assertAlmostEqual(ns["success_rate"], 2 / 3)
                    self.assertEqual(ns["launch_site_counts"].to_dict(),
                                     {"CCAFS SLC 40": 55, "KSC LC 39A": 22, "VAFB SLC 4E": 13})
                    self.assertNotIn("GTO", ns["orbit_counts"].index)
                    self.assertEqual(ns["orbit_counts"].sum(), 63)
                    self.assertEqual(ns["landing_outcomes"].sum(), 90)
                    self.assertEqual(result.FlightNumber.tolist(), list(range(1, 91)))
                    self.assertNotIn("Unnamed: 0", result.columns)

    def test_outcome_labels_do_not_depend_on_frequency_order(self):
        sources = cells(NOTEBOOK)
        define_outcomes = next(s for s in sources if s.startswith("bad_outcomes ="))
        classify = next(s for s in sources if s.startswith("# Task 4:"))
        outcomes = (["False RTLS"] * 10
                    + ["None None", "True Ocean", "True RTLS", "False ASDS",
                       "None ASDS", "False Ocean", "True ASDS"])
        ns = {"df": pd.DataFrame({"Outcome": outcomes})}
        run_cells([define_outcomes, classify], ns)
        self.assertEqual(ns["landing_class"], [0] * 10 + [0, 1, 1, 0, 0, 0, 1])
        for unknown in ("Unexpected", None):
            with self.subTest(unknown=unknown):
                with self.assertRaisesRegex(ValueError, "unrecognized landing outcomes"):
                    run_cells([define_outcomes], {"df": pd.DataFrame({"Outcome": [unknown]})})


if __name__ == "__main__":
    unittest.main()
