# SpaceX Falcon 9 Landing Prediction

IBM Applied Data Science Capstone by Vavan Farizzaman.

This project investigates Falcon 9 first-stage landing outcomes using data collection, exploratory analysis, interactive visualizations, and classification models.

## Final presentation

- **[Final presentation PDF](presentation/output/SpaceX_Capstone_Final_Presentation.pdf)** — the 50-slide report for grading.
- [PowerPoint presentation](presentation/output/SpaceX_Capstone_Final_Presentation.pptx)

The report includes the executive summary, introduction, collection and wrangling methods, charts and SQL results, Folium maps, Plotly Dash results, model comparisons, SVM confusion matrix, conclusions, and evaluation limitations.

## Completed labs

| Stage | Notebook or application |
| --- | --- |
| SpaceX API data collection | [API notebook](jupyter-labs-spacex-data-collection-api-v2.ipynb) |
| Wikipedia web scraping | [Web-scraping notebook](jupyter-labs-webscraping.ipynb) |
| Data wrangling | [Wrangling notebook](labs-jupyter-spacex-Data%20wrangling-v2.ipynb) |
| SQL exploration | [SQLite notebook](jupyter-labs-eda-sql-coursera_sqllite.ipynb) |
| Visual exploration | [EDA charts notebook](jupyter-labs-eda-dataviz-v2.ipynb) |
| Launch-site analysis | [Folium notebook](lab-jupyter-launch-site-location-v2.ipynb) |
| Interactive dashboard | [Plotly Dash application](spacex_dash_app.py) |
| Predictive analysis | [Machine-learning notebook](SpaceX-Machine-Learning-Prediction-Part-5-v1.ipynb) |

## Findings and interpretation

- The main API/EDA/ML sample has **90 launches**, with 60 positive course labels. These include 41 successful drone-ship, 14 ground-pad, and 5 ocean outcomes.
- The SQL dataset has **101 records**. Mission success and booster landing success are different fields.
- The separate **56-record dashboard dataset** gives KSC LC-39A the highest site success rate: 10/13, or 76.9%.
- The classification split has **72 training records and 18 test records**. Logistic regression, SVM, and KNN each classify 15/18 test records correctly (83.33%); the decision tree classifies 13/18 correctly (72.22%).
- Cross-validation with scaling fitted within each training fold selects **SVM**, with 83.57% mean CV accuracy and 83.33% test accuracy. Its test confusion matrix has TN=3, FP=3, FN=0, TP=12.

Dataset sizes and definitions differ across labs; they should not be combined into one denominator. The small holdout, earlier full-dataset preprocessing, and possible temporal dependence limit conclusions about future launches. The notebooks and report distinguish the prescribed course workflow from the additional scaling check.

## Run locally

Use Python 3.9 or later. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install jupyterlab
python -m jupyterlab
```

Open the notebooks from this directory and run them in the lab order above. Saved outputs are included for review. The historical datasets and metadata snapshots in `data/` support reproducibility when the live SpaceX API is unavailable.

Start the dashboard:

```bash
python spacex_dash_app.py --port 8060
```

Open `http://127.0.0.1:8060`. Select a launch site and adjust the payload range to explore the results.

Run the included checks:

```bash
python -m unittest discover -s . -p 'test_*.py' -v
```

## Supporting files

- `data/`: course datasets, archived API metadata, Wikipedia snapshot, and map reference points.
- `dataset_part_1.csv`, `dataset_part_2.csv`, `dataset_part_3.csv`: collected, labelled, and encoded datasets.
- `dataviz_outputs/`: EDA figures.
- `location_outputs/`: interactive Folium HTML maps, site summary, and distances.
- `dashboard_outputs/`: Plotly chart images and interactive HTML exports.
- `ml_outputs/`: comparison tables, confusion matrices, test predictions, and run metadata.
- `presentation/source/`: scripts used to generate the presentation and PDF.
- `RUN_INSTRUCTIONS.txt`: detailed lab notes. Commands there using a `capstone/` prefix assume execution from the parent of the original project folder; omit that prefix when working at this repository's root.

Download HTML visualizations and open them in a browser; GitHub's file viewer does not execute them. Map tiles may require internet access.

To rebuild the presentation with the supplied IBM template and included figure assets:

```bash
python -m pip install -r presentation/requirements.txt
python presentation/source/build_presentation.py
python presentation/source/export_pdf.py
```

## Sources and attribution

The notebooks and presentation retain IBM Skills Network course material and source references. The supplied presentation template and its imagery are from IBM Skills Network. Historical launch tables use Wikipedia revision `1027686922`. Map data is credited to [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). API metadata provenance is recorded in `data/spacex_lab_metadata.json`.

This repository documents an educational analysis of historical course datasets.
