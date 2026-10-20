"""Regression checks for the SQLite assignment and its query boundaries."""
from pathlib import Path
import shutil
import tempfile
import unittest

import nbformat
import pandas as pd

from test_capstone import ROOT, cells, run_cells, working_directory

NOTEBOOK = ROOT / "jupyter-labs-eda-sql-coursera_sqllite.ipynb"


class SQLLabTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cwd = working_directory(self.directory.name)
        self.cwd.__enter__()
        self.addCleanup(self.cwd.__exit__, None, None, None)
        Path("data").mkdir()
        shutil.copyfile(ROOT / "data/Spacex.csv", "data/Spacex.csv")
        self.sources = cells(NOTEBOOK)
        self.ns = run_cells(self.sources)
        self.addCleanup(lambda: self.ns["con"].close())

    def test_all_course_answers_and_rerun(self):
        nbformat.validate(nbformat.read(NOTEBOOK, as_version=4))
        n = self.ns
        self.assertEqual(len(n["df"]), 101)
        self.assertEqual(set(n["task1"].Launch_Site),
                         {"CCAFS LC-40", "CCAFS SLC-40", "KSC LC-39A", "VAFB SLC-4E"})
        self.assertEqual(len(n["task2"]), 5)
        self.assertTrue(n["task2"].Launch_Site.str.startswith("CCA").all())
        self.assertEqual(n["task3"].iloc[0, 0], 45596)
        self.assertAlmostEqual(n["task4"].iloc[0, 0], 2928.4)
        self.assertEqual(n["task5"].iloc[0, 0], "2015-12-22")
        self.assertEqual(set(n["task6"].Booster_Version),
                         {"F9 FT B1022", "F9 FT B1026", "F9 FT  B1021.2", "F9 FT  B1031.2"})
        self.assertEqual(dict(n["task7"].itertuples(index=False, name=None)),
                         {"Success": 100, "Failure": 1})
        self.assertEqual(len(n["task8"]), 12)
        self.assertTrue(n["task8"].PAYLOAD_MASS__KG_.eq(15600).all())
        self.assertEqual(n["task9"].Month_Name.tolist(), ["January", "April"])
        self.assertEqual(n["task10"].Outcome_Count.tolist(), [10, 5, 5, 3, 3, 2, 2, 1])
        run_cells(self.sources, n)
        self.assertEqual(n["run_sql"]("SELECT COUNT(*) FROM SPACEXTABLE").iloc[0, 0], 101)

    def test_blank_dates_and_whitespace_are_cleaned(self):
        raw = self.ns["df"].head(4).copy()
        raw["Date"] = [None, "   ", " 2015-01-10 ", "2015-04-14"]
        raw["Landing_Outcome"] = ["No attempt "] * 4
        raw.to_sql("SPACEXTBL", self.ns["con"], if_exists="replace", index=False)
        cleanup = [s for s in self.sources
                   if 'con.execute("DROP TABLE IF EXISTS SPACEXTABLE")' in s
                   or "CREATE TABLE SPACEXTABLE AS" in s]
        run_cells(cleanup, self.ns)
        result = self.ns["run_sql"]("SELECT * FROM SPACEXTABLE")
        self.assertEqual(result.Date.tolist(), ["2015-01-10", "2015-04-14"])
        self.assertEqual(result.Landing_Outcome.tolist(), ["No attempt", "No attempt"])
        self.assertEqual(self.ns["run_sql"]("SELECT COUNT(*) FROM SPACEXTBL").iloc[0, 0], 4)

    def test_payload_bounds_and_inclusive_date_range(self):
        fixture = pd.DataFrame({
            "Date": ["2010-06-03", "2010-06-04", "2017-03-20", "2017-03-21"],
            "Booster_Version": ["lower-bound", "inside-low", "inside-high", "upper-bound"],
            "PAYLOAD_MASS__KG_": [4000, 4001, 5999, 6000],
            "Landing_Outcome": ["Success (drone ship)"] * 4,
        })
        fixture.to_sql("SPACEXTABLE", self.ns["con"], if_exists="replace", index=False)
        queries = [s for s in self.sources if "task6 = run_sql" in s or "task10 = run_sql" in s]
        run_cells(queries, self.ns)
        self.assertEqual(set(self.ns["task6"].Booster_Version), {"inside-low", "inside-high"})
        self.assertEqual(self.ns["task10"].Outcome_Count.tolist(), [2])


if __name__ == "__main__":
    unittest.main()
