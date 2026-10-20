"""Regression tests; network calls are replaced explicitly with test fixtures."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import nbformat
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
API = ROOT / "jupyter-labs-spacex-data-collection-api-v2.ipynb"
WEB = ROOT / "jupyter-labs-webscraping.ipynb"


def cells(path):
    return [cell.source for cell in nbformat.read(path, as_version=4).cells
            if cell.cell_type == "code"]


def run_cells(sources, namespace=None):
    namespace = {} if namespace is None else namespace
    with contextlib.redirect_stdout(io.StringIO()):
        for source in sources:
            exec(compile(source, "<notebook>", "exec"), namespace)
    return namespace


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class CapstoneTests(unittest.TestCase):
    def web_helpers(self):
        return run_cells([source for source in cells(WEB)
                          if "from bs4 import" in source
                          or source.startswith("def clean_text")])

    def api_helpers(self):
        return run_cells([source for source in cells(API)
                          if source.startswith("import requests\n")
                          or source.startswith("def get")
                          or source.startswith("#Global variables")])

    def test_notebooks_are_valid(self):
        for path in (API, WEB):
            notebook = nbformat.read(path, as_version=4)
            nbformat.validate(notebook)
            self.assertEqual(notebook.metadata.kernelspec.name, "python3")

    def test_scraping_helpers_preserve_text_and_missing_values(self):
        ns = self.web_helpers()
        def cell(html):
            return BeautifulSoup(html, "html.parser").find()
        header = cell("<th><a>Version,<br>Booster</a><sup>[b]</sup></th>")
        before = str(header)
        self.assertEqual(ns["extract_column_from_header"](header), "Version, Booster")
        self.assertEqual(str(header), before)
        self.assertEqual(ns["get_mass"](cell("<td>Classified</td>")), "Classified")
        self.assertIsNone(ns["get_mass"](cell("<td></td>")))
        self.assertEqual(ns["get_mass"](cell("<td>1,200&nbsp;kg (2,646 lb)</td>")),
                         "1,200 kg")
        self.assertEqual(ns["date_time"](cell(
            "<td>4 June 2010,<br>18:45<sup>[1]</sup></td>")),
            ["4 June 2010", "18:45"])
        self.assertEqual(ns["date_time"](cell("<td>4 June 2010</td>")),
                         ["4 June 2010", None])
        self.assertEqual(ns["clean_text"](cell("<td>Unlinked customer</td>")),
                         "Unlinked customer")

    def test_real_wikipedia_snapshot_end_to_end_and_rerun(self):
        html = (ROOT / "data/falcon9_wikipedia_1027686922.html").read_text()
        response = Mock(text=html)
        response.raise_for_status.return_value = None
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            with patch("requests.get", return_value=response):
                ns = run_cells(cells(WEB))
            df = ns["df"]
            self.assertEqual(df["Flight No."].tolist(), list(range(1, 122)))
            self.assertEqual(df.iloc[0]["Date"], "4 June 2010")
            self.assertIn("B0003.1", df.iloc[0]["Version Booster"])
            self.assertEqual(df.iloc[-1]["Date"], "6 June 2021")
            self.assertEqual(len(pd.read_csv("spacex_web_scraped.csv")), len(df))
            self.assertFalse(df["Payload mass"].eq("C").any())
            extraction = next(source for source in cells(WEB)
                              if source.startswith("# Reset the lists"))
            run_cells([extraction], ns)
            self.assertEqual(ns["extracted_row"], len(df))
            self.assertEqual({len(values) for values in ns["launch_dict"].values()},
                             {len(df)})

    def test_api_helpers_keep_null_ids_aligned_and_do_not_duplicate(self):
        ns = self.api_helpers()
        record = {"name": "Falcon 9", "longitude": 1, "latitude": 2,
                  "mass_kg": 1000, "orbit": "LEO", "block": 5,
                  "reuse_count": 2, "serial": "TEST"}
        ns["get_api_record"] = Mock(return_value=record)
        data = pd.DataFrame({
            "rocket": ["rocket", None], "launchpad": ["pad", None],
            "payloads": ["payload", None],
            "cores": [{"core": "core", "flight": 1, "landing_success": True,
                       "landing_type": "ASDS"}, {"core": None}],
        })
        for _ in range(2):
            for name in ("getBoosterVersion", "getLaunchSite", "getPayloadData",
                         "getCoreData"):
                ns[name](data)
        for name in ("BoosterVersion", "Longitude", "Latitude", "LaunchSite",
                     "PayloadMass", "Orbit", "Block", "ReusedCount", "Serial"):
            self.assertEqual(len(ns[name]), 2)
            self.assertIsNone(ns[name][1])
        self.assertEqual(ns["Outcome"], ["True ASDS", "None None"])

    def test_api_http_error_is_not_decoded_as_launch_data(self):
        ns = self.api_helpers()
        ns["USE_LIVE_API"] = True
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("525")
        ns["session"].get = Mock(return_value=response)
        with self.assertRaisesRegex(RuntimeError, "Cannot retrieve"):
            ns["get_api_record"]("rockets", "test")
        response.json.assert_not_called()

    def test_booster_call_cell_replaces_stale_network_lookup(self):
        ns = self.api_helpers()
        ns.pop("USE_LIVE_API")
        stale_lookup = Mock(side_effect=AssertionError("Old network lookup used"))
        ns["get_api_record"] = stale_lookup
        ns["data"] = pd.DataFrame({"rocket": [
            "5e9d0d95eda69955f709d1eb", "5e9d0d95eda69973a809d1ec"
        ]})
        cell = next(source for source in cells(API)
                    if source.startswith("# Call getBoosterVersion"))
        with working_directory(ROOT):
            run_cells([cell], ns)
            run_cells([cell], ns)
        self.assertEqual(ns["BoosterVersion"], ["Falcon 1", "Falcon 9"])
        stale_lookup.assert_not_called()

    def test_api_pipeline_filters_and_imputes_before_export(self):
        # Synthetic fixtures are used only in this test, never saved into notebooks.
        def launch(number, rocket, payload, date="2020-01-01T00:00:00.000Z"):
            return {
                "flight_number": number, "rocket": rocket, "launchpad": "pad",
                "payloads": [payload], "date_utc": date,
                "cores": [{"core": "core", "flight": 1, "landing_success": True,
                           "landing_type": "ASDS", "gridfins": True, "reused": False,
                           "legs": True, "landpad": None}],
            }
        launches = [
            launch(1, "f1", "p1"), launch(2, "f9", "p2"),
            launch(3, "f9", "p3"), launch(4, "f9", "p4", "2021-01-01T00:00:00.000Z"),
            launch(5, "f9", "p5"),
        ]
        launches[-1]["payloads"].append("second-payload")
        records = {
            ("rockets", "f1"): {"name": "Falcon 1"},
            ("rockets", "f9"): {"name": "Falcon 9"},
            ("launchpads", "pad"): {"name": "Test Pad", "longitude": 1, "latitude": 2},
            ("payloads", "p1"): {"mass_kg": 9999, "orbit": "LEO"},
            ("payloads", "p2"): {"mass_kg": 1000, "orbit": "LEO"},
            ("payloads", "p3"): {"mass_kg": None, "orbit": "LEO"},
            ("cores", "core"): {"block": 5, "reuse_count": 0, "serial": "TEST"},
        }
        def get(url, **kwargs):
            self.assertIn("timeout", kwargs)
            response = Mock(status_code=200, text="test fixture")
            response.raise_for_status.return_value = None
            key = tuple(url.rsplit("/", 2)[-2:])
            response.json.return_value = records[key] if key in records else launches
            return response
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            with patch("requests.Session.get", side_effect=get) as request:
                ns = run_cells([source.replace("USE_LIVE_API = False",
                                               "USE_LIVE_API = True")
                                for source in cells(API)])
            df = pd.read_csv("dataset_part_1.csv")
            self.assertEqual(df["FlightNumber"].tolist(), [1, 2])
            self.assertEqual(df["PayloadMass"].tolist(), [1000, 1000])
            self.assertTrue(df["LandingPad"].isna().all())
            self.assertTrue(df["BoosterVersion"].eq("Falcon 9").all())
            self.assertEqual(ns["get_api_record"].cache_info().misses, 7)
            self.assertEqual(request.call_count, 9)

    def test_actual_api_lab_runs_offline_with_verified_metadata(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            shutil.copytree(ROOT / "data", Path("data"))
            with patch("requests.Session.get", side_effect=AssertionError("Unexpected HTTP")):
                ns = run_cells(cells(API))
            self.assertEqual(len(ns["BoosterVersion"]), 94)
            self.assertEqual(ns["BoosterVersion"].count("Falcon 9"), 90)
            self.assertEqual(ns["BoosterVersion"].count("Falcon 1"), 4)
            output = pd.read_csv("dataset_part_1.csv")
            reference = pd.read_csv("data/course_dataset_part_1_reference.csv")
            self.assertEqual(output.shape, (90, 17))
            self.assertTrue(output.PayloadMass.notna().all())
            self.assertGreater(ns["data"].PayloadMass.isna().sum(), 0)
            self.assertEqual(output.FlightNumber.tolist(), list(range(1, 91)))
            # Reference fields should match by date, never by an assumed row order.
            columns = ["Date", "LaunchSite", "Longitude", "Latitude",
                       "Serial", "Block", "ReusedCount", "Flights", "Outcome"]
            pd.testing.assert_frame_equal(
                output[columns].set_index("Date").sort_index(),
                reference[columns].set_index("Date").sort_index(),
                check_dtype=False,
            )
            with self.assertRaisesRegex(KeyError, "No verified"):
                ns["get_api_record"]("rockets", "unknown-id")
            with self.assertRaisesRegex(ValueError, "Restart the kernel"):
                ns["getBoosterVersion"](ns["data"])


if __name__ == "__main__":
    unittest.main()
