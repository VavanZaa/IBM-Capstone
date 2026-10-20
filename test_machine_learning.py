"""Validate the executed ML lab and its exported predictions."""

import json
from pathlib import Path
import tempfile
import unittest

import nbformat
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split

from test_capstone import ROOT, cells, run_cells


NOTEBOOK = ROOT / "SpaceX-Machine-Learning-Prediction-Part-5-v1.ipynb"
OUTPUT = ROOT / "ml_outputs"


class MachineLearningTests(unittest.TestCase):
    def test_prediction_metrics_and_exact_assignment_split(self):
        data = pd.read_csv(ROOT / "dataset_part_2.csv")
        manifest = json.loads((OUTPUT / "run_summary.json").read_text())
        train, test = train_test_split(np.arange(len(data)), test_size=0.2, random_state=2)
        self.assertEqual(manifest["train_indices"], train.tolist())
        self.assertEqual(manifest["test_indices"], test.tolist())
        self.assertEqual((len(train), len(test)), (72, 18))
        self.assertTrue(set(train).isdisjoint(test))
        for workflow in ["course", "fold_scaled"]:
            predictions = pd.read_csv(OUTPUT / f"{workflow}_test_predictions.csv")
            results = pd.read_csv(OUTPUT / f"{workflow}_model_comparison.csv")
            np.testing.assert_array_equal(predictions["FlightNumber"], data.iloc[test]["FlightNumber"])
            np.testing.assert_array_equal(predictions["ActualClass"], data.iloc[test]["Class"])
            self.assertEqual(len(results), 4)
            for row in results.itertuples():
                actual = predictions["ActualClass"]
                predicted = predictions[row.Model]
                self.assertTrue(predicted.isin([0, 1]).all())
                self.assertAlmostEqual(row.TestAccuracy, accuracy_score(actual, predicted))
                np.testing.assert_array_equal(
                    [row.TN, row.FP, row.FN, row.TP],
                    confusion_matrix(actual, predicted, labels=[0, 1]).ravel(),
                )
                self.assertTrue(0 <= row.CVAccuracy <= 1)
                self.assertTrue(np.isfinite(row.CVStd))
        results = pd.read_csv(OUTPUT / "fold_scaled_model_comparison.csv")
        expected = results.loc[results["CVAccuracy"].idxmax(), "Model"]
        self.assertEqual(manifest["fold_scaled_cv_selected_model"], expected)
        self.assertEqual(set(manifest["scaler_training_rows"].values()), {72})

    def test_loader_rejects_misaligned_or_nonfinite_features(self):
        loader = next(source for source in cells(NOTEBOOK)
                      if source.startswith('X = pd.read_csv(ROOT / "dataset_part_3.csv")'))
        data = pd.read_csv(ROOT / "dataset_part_2.csv")
        features = pd.read_csv(ROOT / "dataset_part_3.csv")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features.iloc[::-1].to_csv(root / "dataset_part_3.csv", index=False)
            with self.assertRaisesRegex(ValueError, "not aligned"):
                run_cells([loader], {"pd": pd, "np": np, "ROOT": root, "data": data})
            features.loc[0, "PayloadMass"] = np.inf
            features.to_csv(root / "dataset_part_3.csv", index=False)
            with self.assertRaisesRegex(ValueError, "finite"):
                run_cells([loader], {"pd": pd, "np": np, "ROOT": root, "data": data})

    def test_executed_notebook_and_chart_exports(self):
        notebook = nbformat.read(NOTEBOOK, as_version=4)
        nbformat.validate(notebook)
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        self.assertTrue(all(cell.execution_count is not None for cell in code_cells))
        outputs = [output for cell in code_cells for output in cell.outputs]
        self.assertFalse(any(output.output_type == "error" for output in outputs))
        self.assertEqual(sum("image/png" in output.get("data", {}) for output in outputs), 5)
        self.assertEqual(len(list(OUTPUT.glob("*.png"))), 5)
        for output in outputs:
            if output.output_type == "stream":
                self.assertNotIn("FitFailedWarning", output.text)
                self.assertNotIn("ConvergenceWarning", output.text)


if __name__ == "__main__":
    unittest.main()
