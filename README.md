# KA Performance Dashboard - Single CSV Approach

This is the simplified sharing approach:

```text
Key Accout Report.xlsx
        ↓
build_ka_dashboard_excel_to_single_csv.py
        ↓
ka_dashboard_extract.csv
        ↓
HTML dashboard or Streamlit app
```

## Files

```text
Project Folder/
├─ build_ka_dashboard_excel_to_single_csv.py
├─ KA_Dashboard_Single_CSV_Loader.html
├─ streamlit_app.py
├─ requirements.txt
├─ README.md
├─ Key Accout Report.xlsx             # local source Excel
└─ ka_dashboard_extract.csv           # created by Python
```

## Step 1: Install packages

```bash
pip install -r requirements.txt
```

## Step 2: Create the single CSV from Excel

Put the Excel workbook in the same folder and run:

```bash
python build_ka_dashboard_excel_to_single_csv.py
```

This creates:

```text
ka_dashboard_extract.csv
```

## Step 3: Open HTML manually

Open:

```text
KA_Dashboard_Single_CSV_Loader.html
```

Then select:

```text
ka_dashboard_extract.csv
```

The dashboard loads from that one CSV file.

## Step 4: Run Streamlit

```bash
streamlit run streamlit_app.py
```

Streamlit will read `ka_dashboard_extract.csv` from the same folder. You can also upload the CSV from the sidebar.

## GitHub Upload

For GitHub, upload:

```text
build_ka_dashboard_excel_to_single_csv.py
KA_Dashboard_Single_CSV_Loader.html
streamlit_app.py
requirements.txt
README.md
ka_dashboard_extract.csv
```

Do not upload the Excel workbook if it contains confidential data.

## Updating the dashboard

Whenever the Excel changes:

```bash
python build_ka_dashboard_excel_to_single_csv.py
```

Then replace/commit the new `ka_dashboard_extract.csv`.

## How the CSV works

The CSV has one control column:

```text
__table__
```

This tells the HTML which rows belong to:

```text
outlets
sales
targets
visits
execution
calendar
kpiConfig
meta
kpiTargets
```

The HTML separates the data internally after you upload the CSV.


## Empty tables

If a source such as Execution Standard has no records, the extractor still writes an empty-table marker to the single CSV. This is expected and prevents the dashboard loader from failing when there is no execution data yet.
