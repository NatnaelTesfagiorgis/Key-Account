r"""
Key Account Dashboard V2 - Data Extract Builder
------------------------------------------------
Reads:
    C:\Users\Natnael.Tesfagiorgis\OneDrive - Swinkels\Desktop\python\Key Account\Key Accout Report.xlsx

Creates in:
    ...\Key Account\dashboard_data\

Outputs:
    ka_dashboard_data.json
    outlet_performance.csv
    closed_month_performance_by_outlet.csv
    execution_detail.csv
    visit_detail.csv

Install once:
    python -m pip install pandas openpyxl numpy

Run:
    python build_ka_dashboard_data.py
"""

from __future__ import annotations

import json 
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd 


# =========================================================
# FILE SETTINGS
# =========================================================
BASE_FOLDER = Path(
    r"C:\Users\Natnael.Tesfagiorgis\OneDrive - Swinkels\Desktop\python\Key Account"
)
INPUT_FILE = BASE_FOLDER / "Key Accout Report.xlsx"
OUTPUT_FOLDER = BASE_FOLDER / "dashboard_data"
CSV_OUTPUT_FOLDER = BASE_FOLDER / "dashboard_csv"

OUTPUT_JSON = OUTPUT_FOLDER / "ka_dashboard_data.json"
OUTPUT_OUTLET_CSV = OUTPUT_FOLDER / "outlet_performance.csv"
OUTPUT_CLOSED_MONTH_CSV = OUTPUT_FOLDER / "closed_month_performance_by_outlet.csv"
OUTPUT_EXECUTION_CSV = OUTPUT_FOLDER / "execution_detail.csv"
OUTPUT_VISIT_CSV = OUTPUT_FOLDER / "visit_detail.csv"


# =========================================================
# DEFAULT TARGETS
# Used only when KPI_Config does not contain a Target column.
# =========================================================
DEFAULT_KPI_TARGETS = {
    "Overall KPI": 0.80,
    "Volume": 1.00,
    "JP Adherence": 0.80,
    "Visit Completion": 1.00,
    "Fridge Productivity": 1.00,  # crates per calendar day
    "Execution Standard": 0.85,
}

# =========================================================
# HARDCODED VOLUME CONVERSION TO CRATE EQUIVALENT
# =========================================================
# Standard bottle crate = 24 bottles x 0.33L = 7.92L.
# Standard keg = 30L.
# Therefore:
#   1 keg = 30 / 7.92 = 3.787878... crate equivalent
#
# The dashboard will use "Actual Volume" as crate equivalent.
# The original unconverted sales quantity is kept as "Raw Actual Volume".
BOTTLE_CRATE_LITERS = 24 * 0.33
KEG_LITERS = 30
KEG_TO_CRATE_EQUIVALENT = KEG_LITERS / BOTTLE_CRATE_LITERS


def crate_equivalent_factor(sku: str, category: str) -> float:
    """Return hardcoded conversion factor from source quantity to crate equivalent."""
    sku_text = str(sku or "").strip().lower()
    category_text = str(category or "").strip().lower()

    # Keg / draught products are treated as 30L keg units.
    if "keg" in sku_text or "draught" in sku_text or "draft" in sku_text:
        return KEG_TO_CRATE_EQUIVALENT

    if category_text in {"draught", "draft"}:
        return KEG_TO_CRATE_EQUIVALENT

    # Bottle products are already reported as crate quantity.
    return 1.0


def target_crate_equivalent_factor(category: str) -> float:
    """Return hardcoded target conversion factor from Sales_Target Category to crate equivalent."""
    category_text = str(category or "").strip().lower()
    if category_text in {"draught", "draft"}:
        return KEG_TO_CRATE_EQUIVALENT
    return 1.0


# =========================================================
# GENERAL HELPERS
# =========================================================
def normalize_column_name(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_id(series: pd.Series) -> pd.Series:
    """
    Converts numeric/text IDs to a stable text key.
    Examples:
        1001901.0 -> "1001901"
        " 00123 " -> "00123"
    """
    values = series.copy()

    def clean(value: Any) -> str | None:
        if pd.isna(value):
            return None

        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "nat"}:
            return None

        if re.fullmatch(r"-?\d+\.0+", text):
            text = text.split(".")[0]

        return text

    return values.map(clean)


def parse_excel_date(series: pd.Series) -> pd.Series:
    """
    Handles:
    - Excel dates already read as timestamps
    - Excel serial numbers
    - day-first strings such as 15.06.2026 or 15/06/2026
    """
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    numeric = pd.to_numeric(series, errors="coerce")
    serial_mask = numeric.between(20000, 70000)

    if serial_mask.any():
        parsed.loc[serial_mask] = pd.to_datetime(
            numeric.loc[serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    return parsed.dt.normalize()


def safe_div(numerator: Any, denominator: Any) -> Any:
    if isinstance(denominator, pd.Series):
        result = numerator / denominator.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)

    if denominator in (0, None) or pd.isna(denominator):
        return np.nan

    return numerator / denominator


def capped(value: Any, maximum: float = 1.0) -> float:
    if value is None or pd.isna(value):
        return np.nan
    return float(min(max(value, 0), maximum))


def percentage_value(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(
        series.astype(str).str.replace("%", "", regex=False).str.strip(),
        errors="coerce",
    )
    return numeric.where(numeric <= 1, numeric / 100)


def dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Converts a dataframe to JSON-safe records.
    """
    result = df.copy()

    for column in result.columns:
        if pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = result[column].dt.strftime("%Y-%m-%d")

    result = result.replace([np.inf, -np.inf], np.nan)
    result = result.astype(object).where(pd.notna(result), None)
    return result.to_dict(orient="records")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [json_safe(v) for v in value]

    if isinstance(value, tuple):
        return [json_safe(v) for v in value]

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None

    return value


def find_sheet(sheet_names: list[str], candidates: list[str]) -> str:
    lookup = {name.strip().lower(): name for name in sheet_names}

    for candidate in candidates:
        match = lookup.get(candidate.strip().lower())
        if match:
            return match

    raise KeyError(
        f"Could not find any of these sheets: {candidates}. "
        f"Available sheets: {sheet_names}"
    )


def read_sheet(excel: pd.ExcelFile, candidates: list[str]) -> pd.DataFrame:
    sheet = find_sheet(excel.sheet_names, candidates)
    df = pd.read_excel(excel, sheet_name=sheet, engine="openpyxl")
    df.columns = [normalize_column_name(c) for c in df.columns]
    df = df.dropna(how="all").copy()
    return df


def first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {normalize_column_name(c).lower(): c for c in df.columns}

    for candidate in candidates:
        found = lookup.get(normalize_column_name(candidate).lower())
        if found:
            return found

    return None


def require_column(df: pd.DataFrame, candidates: list[str], source: str) -> str:
    column = first_existing_column(df, candidates)

    if column is None:
        raise KeyError(
            f"{source}: required column not found. "
            f"Expected one of {candidates}; found {list(df.columns)}"
        )

    return column


def build_month_label(series: pd.Series) -> pd.Series:
    return series.dt.strftime("%b %Y")


def working_days_between(
    calendar: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> int:
    if pd.isna(start_date) or pd.isna(end_date):
        return 0

    mask = (
        calendar["Date"].between(start_date, end_date)
        & calendar["Is Working Day"]
    )
    return int(calendar.loc[mask, "Date"].nunique())


def phase_monthly_target_by_working_days(
    monthly_target: pd.Series,
    calendar: pd.DataFrame,
    month_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> pd.Series:
    """
    Prorates a full-month target using Calendar_MDM working days only.
    """
    month_start = pd.Timestamp(month_start).normalize()
    month_end = month_start + pd.offsets.MonthEnd(0)
    capped_end = min(pd.Timestamp(period_end).normalize(), month_end)

    elapsed_working_days = working_days_between(
        calendar,
        month_start,
        capped_end,
    )
    total_working_days = working_days_between(
        calendar,
        month_start,
        month_end,
    )

    if total_working_days == 0:
        raise ValueError(
            f"Calendar_MDM has no working days for "
            f"{month_start.strftime('%B %Y')}."
        )

    return monthly_target * (
        elapsed_working_days / total_working_days
    )


def all_days_between(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
    if pd.isna(start_date) or pd.isna(end_date):
        return 0
    return max(int((end_date - start_date).days) + 1, 0)


# =========================================================
# SOURCE PREPARATION
# =========================================================
def prepare_outlet_master(excel: pd.ExcelFile) -> pd.DataFrame:
    outlet = read_sheet(
        excel,
        ["Outlet_Master_File", "Outlet_Master", "Outlet_Master v1"],
    )

    outlet_id = require_column(outlet, ["Outlet ID", "Account ID"], "Outlet Master")
    outlet_name = require_column(outlet, ["Outlet Name", "Account Name"], "Outlet Master")
    manager = require_column(outlet, ["KA Manager", "Manager"], "Outlet Master")

    employee = first_existing_column(outlet, ["Employee ID"])
    segment = first_existing_column(outlet, ["Segment", "Channel / Segment"])
    status = first_existing_column(outlet, ["Status", "Active Status"])
    fridge = first_existing_column(outlet, ["Fridge Installed"])
    draught = first_existing_column(outlet, ["Draught Installed"])
    area = first_existing_column(outlet, ["Area"])
    region = first_existing_column(outlet, ["Region / City", "Region"])
    remark = first_existing_column(outlet, ["Remark", "Notes"])

    prepared = pd.DataFrame(
        {
            "Outlet ID": normalize_id(outlet[outlet_id]),
            "Outlet Name": outlet[outlet_name].map(normalize_text),
            "KA Manager": outlet[manager].map(normalize_text),
            "Employee ID": normalize_id(outlet[employee]) if employee else None,
            "Segment": outlet[segment].map(normalize_text) if segment else "",
            "Status": outlet[status].map(normalize_text) if status else "Active",
            "Fridge Installed": outlet[fridge].map(normalize_text) if fridge else "No",
            "Draught Installed": outlet[draught].map(normalize_text) if draught else "",
            "Area": outlet[area].map(normalize_text) if area else "",
            "Region / City": outlet[region].map(normalize_text) if region else "",
            "Remark": outlet[remark].map(normalize_text) if remark else "",
        }
    )

    prepared = prepared.dropna(subset=["Outlet ID"])
    prepared["KA Manager"] = prepared["KA Manager"].replace("", "Unassigned")
    prepared["Segment"] = prepared["Segment"].replace("", "Unspecified")

    prepared["Is Active"] = (
        prepared["Status"]
        .str.strip()
        .str.lower()
        .isin({"active", "yes", "y", "1", "true"})
    )

    # Blank status is treated as active for early dummy-data development.
    prepared.loc[prepared["Status"].eq(""), "Is Active"] = True

    prepared["Has Fridge"] = (
        prepared["Fridge Installed"]
        .str.strip()
        .str.lower()
        .isin({"yes", "y", "1", "true"})
    )

    # One reporting owner per outlet.
    prepared = prepared.drop_duplicates("Outlet ID", keep="first")
    return prepared


def prepare_calendar(excel: pd.ExcelFile) -> pd.DataFrame:
    calendar = read_sheet(excel, ["Calander_MDM", "Calendar_MDM", "Calendar"])

    date_col = require_column(calendar, ["Date"], "Calendar")
    working_col = require_column(
        calendar,
        ["Working Day", "Working Day "],
        "Calendar",
    )

    prepared = pd.DataFrame(
        {
            "Date": parse_excel_date(calendar[date_col]),
            "Working Day": calendar[working_col].map(normalize_text),
        }
    ).dropna(subset=["Date"])

    prepared["Is Working Day"] = (
        prepared["Working Day"].str.lower().isin({"yes", "y", "true", "1"})
    )
    prepared = prepared.drop_duplicates("Date").sort_values("Date")
    return prepared


def prepare_product_mdm(excel: pd.ExcelFile) -> pd.DataFrame:
    """
    Product_MDM links Actual_Sales products to Sales_Target categories.

    Required structure:
        Product | Category

    Example:
        Habesha Beer                  Bottle
        Habesha 30L KEG Draught Beer  Draught
    """
    product_mdm = read_sheet(excel, ["Product_MDM", "Product MDM"])

    product_col = require_column(product_mdm, ["Product"], "Product_MDM")
    category_col = require_column(product_mdm, ["Category"], "Product_MDM")

    prepared = pd.DataFrame(
        {
            "SKU": product_mdm[product_col].map(normalize_text),
            "Category": product_mdm[category_col].map(normalize_text),
        }
    )

    prepared = prepared[
        prepared["SKU"].ne("") & prepared["Category"].ne("")
    ].copy()

    prepared["SKU Key"] = prepared["SKU"].str.strip().str.lower()
    prepared["Category"] = prepared["Category"].replace("", "Unspecified")

    duplicate_products = prepared[
        prepared.duplicated("SKU Key", keep=False)
    ]

    if not duplicate_products.empty:
        bad_list = ", ".join(
            sorted(duplicate_products["SKU"].dropna().unique().tolist())
        )
        raise ValueError(
            "Product_MDM has duplicate Product values. "
            f"Please keep one category per product. Duplicates: {bad_list}"
        )

    return prepared[["SKU Key", "SKU", "Category"]]


def prepare_actual_sales(
    excel: pd.ExcelFile,
    product_mdm: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    sales = read_sheet(excel, ["Actual_Sales", "Actual Sales"])

    date_col = require_column(sales, ["Calendar Day", "Date"], "Actual Sales")
    outlet_col = require_column(
        sales,
        ["Outlet ID", "Account ID (Account)", "Account ID"],
        "Actual Sales",
    )
    qty_col = require_column(
        sales,
        ["Requested Quantity", "Quantity", "Actual"],
        "Actual Sales",
    )
    sku_col = require_column(sales, ["Product", "SKU"], "Actual Sales")
    sales_unit_col = first_existing_column(sales, ["Sales Unit"])

    prepared = pd.DataFrame(
        {
            "Date": parse_excel_date(sales[date_col]),
            "Outlet ID": normalize_id(sales[outlet_col]),
            "SKU": sales[sku_col].map(normalize_text),
            "Sales Unit": sales[sales_unit_col].map(normalize_text) if sales_unit_col else "",
            "Actual Volume": pd.to_numeric(sales[qty_col], errors="coerce").fillna(0),
        }
    )

    prepared = prepared.dropna(subset=["Date", "Outlet ID"])
    prepared["SKU"] = prepared["SKU"].replace("", "Unspecified")
    prepared["SKU Key"] = prepared["SKU"].str.strip().str.lower()

    prepared = prepared.merge(
        product_mdm[["SKU Key", "Category"]],
        on="SKU Key",
        how="left",
    )

    unmatched_product_count = int(
        prepared["Category"].isna().sum()
    )

    # Keep unmatched products visible but do not silently classify them as Bottle.
    # They will not connect correctly to Bottle/Draught target until added to Product_MDM.
    prepared["Category"] = prepared["Category"].fillna("Unmapped")

    # Convert all actual sales to crate equivalent in code.
    # Bottle/crate products stay as-is.
    # Keg/draught products are converted using 1 x 30L keg = 30 / 7.92 = 3.787878 crate equivalent.
    prepared["Raw Actual Volume"] = prepared["Actual Volume"]
    prepared["Crate Equivalent Factor"] = [
        crate_equivalent_factor(sku, category)
        for sku, category in zip(prepared["SKU"], prepared["Category"])
    ]
    prepared["Actual Volume"] = (
        prepared["Raw Actual Volume"] * prepared["Crate Equivalent Factor"]
    )

    return prepared.drop(columns=["SKU Key"]), unmatched_product_count

def prepare_sales_target(
    excel: pd.ExcelFile,
    fallback_month: pd.Timestamp,
) -> tuple[pd.DataFrame, bool]:
    """
    Reads the monthly outlet target table.

    The official sheet name is now Sales_Target and Date is expected in the
    first column. The month of Date determines which month each target belongs
    to, so MTD, YTD and closed-month calculations use the correct target period.
    """
    target = read_sheet(excel, ["Sales_Target"])

    date_col = require_column(target, ["Date"], "Sales_Target")
    outlet_col = require_column(target, ["Outlet ID"], "Sales_Target")
    target_col = require_column(target, ["Target"], "Sales_Target")

    employee_col = first_existing_column(target, ["Employee ID"])
    sku_col = first_existing_column(target, ["SKU", "Product"])
    category_col = require_column(target, ["Category"], "Sales_Target")

    # Sales_Target commonly uses month-start values such as 7/1/2026.
    # Parse without forcing day-first, because forcing day-first would read
    # 7/1/2026 as 7 January instead of 1 July.
    parsed_dates = pd.to_datetime(
        target[date_col],
        errors="coerce",
        dayfirst=False,
    )

    numeric_dates = pd.to_numeric(target[date_col], errors="coerce")
    excel_serial_mask = numeric_dates.between(20000, 70000)

    if excel_serial_mask.any():
        parsed_dates.loc[excel_serial_mask] = pd.to_datetime(
            numeric_dates.loc[excel_serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    parsed_dates = parsed_dates.dt.normalize()

    prepared = pd.DataFrame(
        {
            "Target Date": parsed_dates,
            "Target Month": parsed_dates.dt.to_period("M").dt.to_timestamp(),
            "Outlet ID": normalize_id(target[outlet_col]),
            "Employee ID": (
                normalize_id(target[employee_col])
                if employee_col
                else None
            ),
            "SKU": (
                target[sku_col].map(normalize_text)
                if sku_col
                else "Unspecified"
            ),
            "Category": target[category_col].map(normalize_text),
            "Full Month Target": pd.to_numeric(
                target[target_col],
                errors="coerce",
            ).fillna(0),
        }
    )

    invalid_date_count = int(
        (
            prepared["Target Date"].isna()
            & prepared["Outlet ID"].notna()
        ).sum()
    )

    if invalid_date_count:
        raise ValueError(
            f"Sales_Target contains {invalid_date_count} row(s) with an "
            "invalid or blank Date. Correct those dates before rebuilding "
            "the dashboard."
        )

    prepared = prepared.dropna(
        subset=["Target Date", "Target Month", "Outlet ID"]
    ).copy()

    # Normalize the reporting key to the first day of the month.
    # This prevents date-format ambiguity from blocking the dashboard.
    prepared["Target Month"] = (
        prepared["Target Date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    prepared["SKU"] = prepared["SKU"].replace("", "Unspecified")
    prepared["Category"] = prepared["Category"].replace(
        "",
        "Unspecified",
    )

    # Convert Sales_Target to crate equivalent in code.
    # Bottle category targets are already entered as crate quantity.
    # Draught category targets are entered as keg count and converted:
    # 1 x 30L keg = 30 / 7.92 = 3.787878 crate equivalent.
    prepared["Raw Full Month Target"] = prepared["Full Month Target"]
    prepared["Target Crate Equivalent Factor"] = prepared["Category"].apply(
        target_crate_equivalent_factor
    )
    prepared["Full Month Target"] = (
        prepared["Raw Full Month Target"] * prepared["Target Crate Equivalent Factor"]
    )

    # Date is now mandatory, so the fallback is no longer used.
    fallback_used = False
    return prepared, fallback_used


def prepare_visit_plan(excel: pd.ExcelFile) -> pd.DataFrame:
    plan = read_sheet(excel, ["Visit_Plan", "Visit Plan"])

    date_col = require_column(plan, ["Date"], "Visit Plan")
    outlet_col = require_column(plan, ["Outlet ID", "ID"], "Visit Plan")
    employee_col = first_existing_column(plan, ["Employee ID"])

    prepared = pd.DataFrame(
        {
            "Date": parse_excel_date(plan[date_col]),
            "Outlet ID": normalize_id(plan[outlet_col]),
            "Employee ID": normalize_id(plan[employee_col]) if employee_col else None,
        }
    )

    prepared = prepared.dropna(subset=["Date", "Outlet ID"])
    return prepared


def prepare_visit_actual(excel: pd.ExcelFile) -> pd.DataFrame:
    actual = read_sheet(excel, ["Visit_Actual", "Visit Actual"])

    date_col = require_column(
        actual,
        ["End Date in Local Time Zone", "Date", "Visit Date"],
        "Visit Actual",
    )
    outlet_col = require_column(
        actual,
        ["Outlet ID", "Account", "Account ID"],
        "Visit Actual",
    )
    count_col = first_existing_column(
        actual,
        ["1 Visits Account", "Visit Count", "Visits"],
    )
    employee_col = first_existing_column(
        actual,
        ["Employee Responsible For Account", "Employee ID"],
    )

    prepared = pd.DataFrame(
        {
            "Date": parse_excel_date(actual[date_col]),
            "Outlet ID": normalize_id(actual[outlet_col]),
            "Employee ID": normalize_id(actual[employee_col]) if employee_col else None,
            "Visit Count": (
                pd.to_numeric(actual[count_col], errors="coerce").fillna(1)
                if count_col
                else 1
            ),
        }
    )

    prepared = prepared.dropna(subset=["Date", "Outlet ID"])
    return prepared


def prepare_execution_standard(
    excel: pd.ExcelFile,
    default_target: float,
) -> pd.DataFrame:
    execution = read_sheet(
        excel,
        ["Execution_Standard", "Execution Standard"],
    )

    outlet_col = require_column(execution, ["Outlet ID"], "Execution Standard")
    name_col = first_existing_column(execution, ["Name", "KA Manager"])
    date_col = first_existing_column(execution, ["Date", "Data"])
    actual_col = first_existing_column(
        execution,
        [
            "Execution Standard Actual",
            "Execution Standard",
            "Execution Standard ",
        ],
    )
    target_col = first_existing_column(
        execution,
        ["Execution Standard Target"],
    )
    comment_col = first_existing_column(execution, ["Comment"])
    done_by_col = first_existing_column(execution, ["Done By"])

    if actual_col is None:
        raise KeyError(
            "Execution Standard: could not find Actual column. "
            "Expected 'Execution Standard Actual' or 'Execution Standard'."
        )

    prepared = pd.DataFrame(
        {
            "Outlet ID": normalize_id(execution[outlet_col]),
            "Name": execution[name_col].map(normalize_text) if name_col else "",
            "Date": parse_excel_date(execution[date_col]) if date_col else pd.NaT,
            "Execution Actual": percentage_value(execution[actual_col]),
            "Execution Target": (
                percentage_value(execution[target_col])
                if target_col
                else default_target
            ),
            "Comment": execution[comment_col].map(normalize_text) if comment_col else "",
            "Done By": execution[done_by_col].map(normalize_text) if done_by_col else "",
        }
    )

    if prepared["Date"].isna().all():
        prepared["Date"] = pd.Timestamp.today().normalize()

    prepared = prepared.dropna(subset=["Outlet ID", "Date"])
    prepared["Execution Achievement"] = safe_div(
        prepared["Execution Actual"],
        prepared["Execution Target"],
    )
    return prepared


def prepare_kpi_config(excel: pd.ExcelFile) -> tuple[pd.DataFrame, dict[str, float]]:
    config = read_sheet(excel, ["KPI_Config", "KPI Config"])

    kpi_col = require_column(config, ["KPI"], "KPI Config")
    weight_col = require_column(config, ["Weight %"], "KPI Config")
    final_col = first_existing_column(config, ["Included in Final KPI"])
    provisional_col = first_existing_column(config, ["Included in Provisional KPI"])
    target_col = first_existing_column(config, ["Target", "Target %", "KPI Target"])

    prepared = pd.DataFrame(
        {
            "KPI": config[kpi_col].map(normalize_text),
            "Weight": percentage_value(config[weight_col]),
            "Included Final": (
                config[final_col].map(normalize_text).str.lower().eq("yes")
                if final_col
                else True
            ),
            "Included Provisional": (
                config[provisional_col].map(normalize_text).str.lower().eq("yes")
                if provisional_col
                else True
            ),
        }
    )

    prepared = prepared[prepared["KPI"].ne("")].copy()
    prepared["KPI"] = prepared["KPI"].replace(
        {"Cold Coverage": "Fridge Productivity"}
    )

    targets = DEFAULT_KPI_TARGETS.copy()

    if target_col:
        parsed_target = percentage_value(config[target_col])
        for kpi, value in zip(prepared["KPI"], parsed_target):
            if pd.notna(value):
                targets[kpi] = float(value)

    return prepared, targets


# =========================================================
# ANALYTICAL BUILD
# =========================================================
def create_daily_visit_detail(
    plan: pd.DataFrame,
    actual: pd.DataFrame,
    outlet_dim: pd.DataFrame,
) -> pd.DataFrame:
    planned = (
        plan.groupby(["Date", "Outlet ID"], as_index=False)
        .size()
        .rename(columns={"size": "Planned Visits"})
    )

    actual_grouped = (
        actual.groupby(["Date", "Outlet ID"], as_index=False)["Visit Count"]
        .sum()
        .rename(columns={"Visit Count": "Actual Visits"})
    )

    detail = planned.merge(
        actual_grouped,
        on=["Date", "Outlet ID"],
        how="outer",
    )

    detail["Planned Visits"] = detail["Planned Visits"].fillna(0)
    detail["Actual Visits"] = detail["Actual Visits"].fillna(0)

    # Visits that occurred on the planned outlet/date count as JP-good,
    # capped to the number of actual visits for that outlet/date.
    detail["JP Good Visits"] = np.where(
        detail["Planned Visits"] > 0,
        detail["Actual Visits"],
        0,
    )

    detail["Visit Completion"] = safe_div(
        detail["Actual Visits"],
        detail["Planned Visits"],
    )

    detail["JP Adherence"] = safe_div(
        detail["JP Good Visits"],
        detail["Actual Visits"],
    )

    detail = detail.merge(
        outlet_dim[
            ["Outlet ID", "Outlet Name", "KA Manager", "Segment"]
        ],
        on="Outlet ID",
        how="left",
    )
    return detail


def create_period_outlet_metrics(
    *,
    outlet_dim: pd.DataFrame,
    sales: pd.DataFrame,
    targets: pd.DataFrame,
    visit_detail: pd.DataFrame,
    execution: pd.DataFrame,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    target_months: list[pd.Timestamp],
    calendar_day_count: int,
    prefix: str,
) -> pd.DataFrame:
    base = outlet_dim.copy()

    sales_period = sales[sales["Date"].between(period_start, period_end)].copy()
    sales_outlet = (
        sales_period.groupby("Outlet ID", as_index=False)["Actual Volume"]
        .sum()
        .rename(columns={"Actual Volume": f"{prefix} Volume Actual"})
    )

    selected_targets = targets[targets["Target Month"].isin(target_months)].copy()
    target_outlet = (
        selected_targets.groupby("Outlet ID", as_index=False)["Full Month Target"]
        .sum()
        .rename(columns={"Full Month Target": f"{prefix} Volume Target"})
    )

    visits_period = visit_detail[
        visit_detail["Date"].between(period_start, period_end)
    ].copy()

    visits_outlet = (
        visits_period.groupby("Outlet ID", as_index=False)
        .agg(
            **{
                f"{prefix} Planned Visits": ("Planned Visits", "sum"),
                f"{prefix} Actual Visits": ("Actual Visits", "sum"),
                f"{prefix} JP Good Visits": ("JP Good Visits", "sum"),
            }
        )
    )

    latest_execution = (
        execution[execution["Date"].between(period_start, period_end)]
        .sort_values(["Outlet ID", "Date"])
        .drop_duplicates("Outlet ID", keep="last")
        [
            [
                "Outlet ID",
                "Date",
                "Execution Actual",
                "Execution Target",
                "Execution Achievement",
                "Done By",
                "Comment",
            ]
        ]
        .rename(
            columns={
                "Date": f"{prefix} Execution Date",
                "Execution Actual": f"{prefix} Execution Actual",
                "Execution Target": f"{prefix} Execution Target",
                "Execution Achievement": f"{prefix} Execution Achievement",
                "Done By": f"{prefix} Execution Done By",
                "Comment": f"{prefix} Execution Comment",
            }
        )
    )

    result = (
        base.merge(sales_outlet, on="Outlet ID", how="left")
        .merge(target_outlet, on="Outlet ID", how="left")
        .merge(visits_outlet, on="Outlet ID", how="left")
        .merge(latest_execution, on="Outlet ID", how="left")
    )

    numeric_fill = [
        f"{prefix} Volume Actual",
        f"{prefix} Volume Target",
        f"{prefix} Planned Visits",
        f"{prefix} Actual Visits",
        f"{prefix} JP Good Visits",
    ]

    for column in numeric_fill:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)

    result[f"{prefix} Volume Achievement"] = safe_div(
        result[f"{prefix} Volume Actual"],
        result[f"{prefix} Volume Target"],
    )

    result[f"{prefix} Visit Completion"] = safe_div(
        result[f"{prefix} Actual Visits"],
        result[f"{prefix} Planned Visits"],
    )

    result[f"{prefix} JP Adherence"] = safe_div(
        result[f"{prefix} JP Good Visits"],
        result[f"{prefix} Actual Visits"],
    )

    # Fridge productivity uses ALL calendar days, per the final agreed rule.
    result[f"{prefix} Fridge Productivity"] = np.where(
        result["Has Fridge"] & (calendar_day_count > 0),
        result[f"{prefix} Volume Actual"] / calendar_day_count,
        np.nan,
    )

    return result


def resolve_input_workbook() -> Path:
    """
    Find the Excel workbook dynamically.

    This prevents the script from depending only on the old hard-coded path:
    C:\\Users\\Natnael.Tesfagiorgis\\OneDrive - Swinkels\\Desktop\\python\\Key Account\\Key Accout Report.xlsx

    Priority:
    1. INPUT_FILE if it exists
    2. Excel file beside this Python script
    3. Excel file in the current working directory / notebook folder
    4. Any nearby .xlsx file that contains the required Outlet_Master_File sheet
    """
    candidates: list[Path] = []

    # Original hard-coded path, if valid on this machine
    candidates.append(INPUT_FILE)

    # Same folder as this Python file
    try:
        script_folder = Path(__file__).resolve().parent
        candidates.extend(
            [
                script_folder / "Key Accout Report.xlsx",
                script_folder / "Key Account Report.xlsx",
            ]
        )
        candidates.extend(script_folder.glob("*.xlsx"))
    except NameError:
        pass

    # Current working directory, useful when running from Jupyter / interactive cells
    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / "Key Accout Report.xlsx",
            cwd / "Key Account Report.xlsx",
        ]
    )
    candidates.extend(cwd.glob("*.xlsx"))

    checked: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen or candidate.name.startswith("~$"):
            continue
        seen.add(key)

        if not candidate.exists():
            checked.append(f"{candidate} -> not found")
            continue

        try:
            xls = pd.ExcelFile(candidate, engine="openpyxl")
            sheets = set(xls.sheet_names)
        except Exception as exc:
            checked.append(f"{candidate} -> could not read: {exc}")
            continue

        # Correct KA workbook must have outlet master sheet.
        if sheets.intersection({"Outlet_Master_File", "Outlet_Master", "Outlet_Master v1"}):
            return candidate

        checked.append(f"{candidate} -> wrong workbook; sheets: {list(sheets)[:10]}")

    raise FileNotFoundError(
        "Could not find the correct KA Excel workbook.\n\n"
        "Put the full KA workbook in the same folder as this Python file and name it:\n"
        "Key Accout Report.xlsx\n\n"
        "The workbook must contain the Outlet_Master_File sheet.\n\n"
        "Checked:\n" + "\n".join(checked[:30])
    )

def build_dashboard_extract() -> dict[str, Any]:
    input_file = resolve_input_workbook()

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    excel = pd.ExcelFile(input_file, engine="openpyxl")

    outlet = prepare_outlet_master(excel)
    calendar = prepare_calendar(excel)
    product_mdm = prepare_product_mdm(excel)
    sales, unmatched_product_count = prepare_actual_sales(excel, product_mdm)

    if sales.empty:
        raise ValueError("Actual_Sales contains no usable rows.")

    latest_date = sales["Date"].max()
    current_month_start = latest_date.to_period("M").to_timestamp()
    current_year_start = pd.Timestamp(latest_date.year, 1, 1)
    current_month_end = current_month_start + pd.offsets.MonthEnd(0)

    target, target_fallback_used = prepare_sales_target(excel, latest_date)
    visit_plan = prepare_visit_plan(excel)
    visit_actual = prepare_visit_actual(excel)
    kpi_config, kpi_targets = prepare_kpi_config(excel)
    execution = prepare_execution_standard(
        excel,
        kpi_targets["Execution Standard"],
    )

    # Keep only KA outlets after outlet-level sales preparation.
    sales = sales.merge(
        outlet[["Outlet ID"]],
        on="Outlet ID",
        how="inner",
    )

    visit_plan = visit_plan.merge(
        outlet[["Outlet ID"]],
        on="Outlet ID",
        how="inner",
    )

    visit_actual = visit_actual.merge(
        outlet[["Outlet ID"]],
        on="Outlet ID",
        how="inner",
    )

    execution = execution.merge(
        outlet[["Outlet ID"]],
        on="Outlet ID",
        how="inner",
    )

    visit_detail = create_daily_visit_detail(
        visit_plan,
        visit_actual,
        outlet,
    )

    mtd_all_days = all_days_between(current_month_start, latest_date)
    ytd_all_days = all_days_between(current_year_start, latest_date)
    last_day_count = 1

    current_target_months = [current_month_start]
    ytd_target_months = list(
        pd.date_range(current_year_start, current_month_start, freq="MS")
    )

    # Last Day
    last_day = create_period_outlet_metrics(
        outlet_dim=outlet,
        sales=sales,
        targets=target,
        visit_detail=visit_detail,
        execution=execution,
        period_start=latest_date,
        period_end=latest_date,
        target_months=current_target_months,
        calendar_day_count=last_day_count,
        prefix="Last Day",
    )

    # Last-day target is the monthly target divided by working days only.
    # Non-working days receive a target of zero.
    latest_is_working_day = bool(
        calendar.loc[
            calendar["Date"].eq(latest_date),
            "Is Working Day",
        ].any()
    )

    current_month_working_days = working_days_between(
        calendar,
        current_month_start,
        current_month_end,
    )

    if current_month_working_days == 0:
        raise ValueError(
            f"Calendar_MDM has no working days for "
            f"{current_month_start.strftime('%B %Y')}."
        )

    last_day["Last Day Volume Target"] = np.where(
        latest_is_working_day,
        last_day["Last Day Volume Target"]
        / current_month_working_days,
        0,
    )
    last_day["Last Day Volume Achievement"] = safe_div(
        last_day["Last Day Volume Actual"],
        last_day["Last Day Volume Target"],
    )

    # MTD
    mtd = create_period_outlet_metrics(
        outlet_dim=outlet,
        sales=sales,
        targets=target,
        visit_detail=visit_detail,
        execution=execution,
        period_start=current_month_start,
        period_end=latest_date,
        target_months=current_target_months,
        calendar_day_count=mtd_all_days,
        prefix="MTD",
    )

    # Sales_Target stores one full-month target row dated on the first day
    # of the month. Phase that target using Calendar_MDM working days only.
    elapsed_working_days = working_days_between(
        calendar,
        current_month_start,
        latest_date,
    )
    full_month_working_days = working_days_between(
        calendar,
        current_month_start,
        current_month_end,
    )

    mtd["MTD Full Month Target"] = mtd["MTD Volume Target"]
    mtd["MTD Volume Target"] = phase_monthly_target_by_working_days(
        monthly_target=mtd["MTD Full Month Target"],
        calendar=calendar,
        month_start=current_month_start,
        period_end=latest_date,
    )
    mtd["MTD Volume Achievement"] = safe_div(
        mtd["MTD Volume Actual"],
        mtd["MTD Volume Target"],
    )

    # YTD
    ytd = create_period_outlet_metrics(
        outlet_dim=outlet,
        sales=sales,
        targets=target,
        visit_detail=visit_detail,
        execution=execution,
        period_start=current_year_start,
        period_end=latest_date,
        target_months=ytd_target_months,
        calendar_day_count=ytd_all_days,
        prefix="YTD",
    )

    # Combine outlet table.
    key_columns = [
        "Outlet ID",
        "Outlet Name",
        "KA Manager",
        "Segment",
        "Is Active",
        "Has Fridge",
    ]

    outlet_table = outlet[key_columns].copy()

    last_day_metrics = [
        "Outlet ID",
        "Last Day Volume Actual",
        "Last Day Volume Target",
        "Last Day Volume Achievement",
        "Last Day Visit Completion",
        "Last Day JP Adherence",
        "Last Day Fridge Productivity",
        "Last Day Execution Actual",
        "Last Day Execution Target",
        "Last Day Execution Achievement",
    ]

    mtd_metrics = [
        "Outlet ID",
        "MTD Volume Actual",
        "MTD Volume Target",
        "MTD Volume Achievement",
        "MTD Visit Completion",
        "MTD JP Adherence",
        "MTD Fridge Productivity",
        "MTD Execution Actual",
        "MTD Execution Target",
        "MTD Execution Achievement",
        "MTD Execution Date",
        "MTD Execution Done By",
        "MTD Execution Comment",
    ]

    ytd_metrics = [
        "Outlet ID",
        "YTD Volume Actual",
        "YTD Volume Target",
        "YTD Volume Achievement",
        "YTD Visit Completion",
        "YTD JP Adherence",
        "YTD Fridge Productivity",
        "YTD Execution Actual",
        "YTD Execution Target",
        "YTD Execution Achievement",
    ]

    outlet_table = (
        outlet_table.merge(last_day[last_day_metrics], on="Outlet ID", how="left")
        .merge(mtd[mtd_metrics], on="Outlet ID", how="left")
        .merge(ytd[ytd_metrics], on="Outlet ID", how="left")
    )

    outlet_table["Status"] = np.select(
        [
            outlet_table["MTD Volume Achievement"].ge(0.90),
            outlet_table["MTD Volume Achievement"].ge(0.75),
            outlet_table["MTD Volume Achievement"].ge(0.50),
        ],
        ["On Track", "Watch", "At Risk"],
        default="Critical",
    )

    # Current KPI summary.
    active_outlets = outlet_table[outlet_table["Is Active"]].copy()
    total_actual = float(active_outlets["MTD Volume Actual"].sum())
    total_target = float(active_outlets["MTD Volume Target"].sum())
    volume_achievement = safe_div(total_actual, total_target)

    total_planned_visits = float(
        visit_detail[
            visit_detail["Date"].between(current_month_start, latest_date)
        ]["Planned Visits"].sum()
    )
    total_actual_visits = float(
        visit_detail[
            visit_detail["Date"].between(current_month_start, latest_date)
        ]["Actual Visits"].sum()
    )
    total_jp_good = float(
        visit_detail[
            visit_detail["Date"].between(current_month_start, latest_date)
        ]["JP Good Visits"].sum()
    )

    visit_completion = safe_div(total_actual_visits, total_planned_visits)
    jp_adherence = safe_div(total_jp_good, total_actual_visits)

    latest_exec = (
        execution[execution["Date"].between(current_month_start, latest_date)]
        .sort_values(["Outlet ID", "Date"])
        .drop_duplicates("Outlet ID", keep="last")
    )

    execution_actual = (
        float(latest_exec["Execution Actual"].mean())
        if not latest_exec.empty
        else np.nan
    )
    execution_target = (
        float(latest_exec["Execution Target"].mean())
        if not latest_exec.empty
        else kpi_targets["Execution Standard"]
    )
    execution_achievement = safe_div(execution_actual, execution_target)

    fridge_outlets = active_outlets[active_outlets["Has Fridge"]].copy()
    fridge_productivity = (
        float(fridge_outlets["MTD Volume Actual"].sum())
        / (len(fridge_outlets) * mtd_all_days)
        if len(fridge_outlets) > 0 and mtd_all_days > 0
        else np.nan
    )

    zero_sales_count = int(
        active_outlets["MTD Volume Actual"].fillna(0).le(0).sum()
    )

    # Weighted overall KPI.
    kpi_value_map = {
        "Volume": capped(volume_achievement),
        "JP Adherence": capped(jp_adherence),
        "Execution Standard": capped(execution_achievement),
        "Visit Completion": capped(visit_completion),
        "Fridge Productivity": capped(
            safe_div(fridge_productivity, kpi_targets["Fridge Productivity"])
        ),
    }

    weighted_score = 0.0
    used_weight = 0.0

    for _, row in kpi_config.iterrows():
        if not bool(row["Included Final"]):
            continue

        kpi_name = row["KPI"]
        value = kpi_value_map.get(kpi_name)
        weight = row["Weight"]

        if pd.notna(value) and pd.notna(weight):
            weighted_score += float(value) * float(weight)
            used_weight += float(weight)

    overall_kpi = safe_div(weighted_score, used_weight)

    kpi_cards = [
        {
            "key": "overall_kpi",
            "title": "Overall KPI",
            "actual": overall_kpi,
            "target": kpi_targets["Overall KPI"],
            "format": "percent",
        },
        {
            "key": "volume_achievement",
            "title": "Volume Achievement",
            "actual": volume_achievement,
            "target": kpi_targets["Volume"],
            "format": "percent",
            "detailActual": total_actual,
            "detailTarget": total_target,
        },
        {
            "key": "jp_adherence",
            "title": "JP Adherence",
            "actual": jp_adherence,
            "target": kpi_targets["JP Adherence"],
            "format": "percent",
        },
        {
            "key": "visit_completion",
            "title": "Visit Completion",
            "actual": visit_completion,
            "target": kpi_targets["Visit Completion"],
            "format": "percent",
        },
        {
            "key": "fridge_productivity",
            "title": "Fridge Productivity",
            "actual": fridge_productivity,
            "target": kpi_targets["Fridge Productivity"],
            "format": "decimal",
        },
        {
            "key": "zero_sales_outlets",
            "title": "Zero-Sales Outlets",
            "actual": zero_sales_count,
            "target": None,
            "format": "integer",
            "detailTotal": int(len(active_outlets)),
        },
        {
            "key": "execution_standard",
            "title": "Execution Standard",
            "actual": execution_actual,
            "target": execution_target,
            "format": "percent",
        },
    ]

    # Daily volume combo chart.
    daily_sales = (
        sales[sales["Date"].between(current_month_start, latest_date)]
        .groupby("Date", as_index=False)["Actual Volume"]
        .sum()
    )

    daily_target_value = safe_div(total_target, elapsed_working_days)
    daily_sales["Target"] = np.where(
        daily_sales["Date"].isin(
            calendar.loc[
                calendar["Date"].between(current_month_start, latest_date)
                & calendar["Is Working Day"],
                "Date",
            ]
        ),
        daily_target_value,
        0,
    )
    daily_sales["Achievement"] = safe_div(
        daily_sales["Actual Volume"],
        daily_sales["Target"],
    )

    # Manager volume.
    manager_volume = (
        active_outlets.groupby("KA Manager", as_index=False)
        .agg(
            Actual=("MTD Volume Actual", "sum"),
            Target=("MTD Volume Target", "sum"),
        )
    )
    manager_volume["Achievement"] = safe_div(
        manager_volume["Actual"],
        manager_volume["Target"],
    )

    # Daily visits.
    daily_visits = (
        visit_detail[
            visit_detail["Date"].between(current_month_start, latest_date)
        ]
        .groupby("Date", as_index=False)
        .agg(
            Planned=("Planned Visits", "sum"),
            Actual=("Actual Visits", "sum"),
        )
    )
    daily_visits["Achievement"] = safe_div(
        daily_visits["Actual"],
        daily_visits["Planned"],
    )

    # Execution by manager.
    execution_manager = (
        latest_exec.merge(
            outlet[["Outlet ID", "KA Manager"]],
            on="Outlet ID",
            how="left",
        )
        .groupby("KA Manager", as_index=False)
        .agg(
            Actual=("Execution Actual", "mean"),
            Target=("Execution Target", "mean"),
        )
    )
    execution_manager["Achievement"] = safe_div(
        execution_manager["Actual"],
        execution_manager["Target"],
    )

    # Fridge productivity by manager.
    manager_fridge = (
        fridge_outlets.groupby("KA Manager", as_index=False)
        .agg(
            Total_Volume=("MTD Volume Actual", "sum"),
            Fridge_Outlets=("Outlet ID", "nunique"),
        )
    )
    manager_fridge["Actual"] = safe_div(
        manager_fridge["Total_Volume"],
        manager_fridge["Fridge_Outlets"] * mtd_all_days,
    )
    manager_fridge["Target"] = kpi_targets["Fridge Productivity"]
    manager_fridge["Achievement"] = safe_div(
        manager_fridge["Actual"],
        manager_fridge["Target"],
    )

    # Fridge breakdown at outlet level.
    fridge_outlets["Fridge Class"] = np.select(
        [
            fridge_outlets["MTD Fridge Productivity"].ge(1),
            fridge_outlets["MTD Fridge Productivity"].gt(0),
        ],
        ["Productive", "Underproductive"],
        default="Inactive",
    )

    fridge_breakdown = (
        fridge_outlets.groupby("Fridge Class", as_index=False)
        .agg(Outlets=("Outlet ID", "nunique"))
    )

    total_fridge = int(fridge_breakdown["Outlets"].sum())
    fridge_breakdown["Share"] = safe_div(
        fridge_breakdown["Outlets"],
        total_fridge,
    )

    # Closed-month performance by outlet.
    closed_month_start = current_month_start - pd.offsets.MonthBegin(1)
    closed_months = list(
        pd.date_range(
            start=pd.Timestamp(latest_date.year, 1, 1),
            end=closed_month_start,
            freq="MS",
        )
    )

    closed_rows: list[pd.DataFrame] = []

    for month_start in closed_months:
        month_end = month_start + pd.offsets.MonthEnd(0)
        month_all_days = int(month_end.day)

        month_result = create_period_outlet_metrics(
            outlet_dim=outlet,
            sales=sales,
            targets=target,
            visit_detail=visit_detail,
            execution=execution,
            period_start=month_start,
            period_end=month_end,
            target_months=[month_start],
            calendar_day_count=month_all_days,
            prefix="Closed Month",
        )

        month_result.insert(0, "Month", month_start.strftime("%b %Y"))

        closed_rows.append(
            month_result[
                [
                    "Month",
                    "Outlet ID",
                    "Outlet Name",
                    "KA Manager",
                    "Segment",
                    "Closed Month Volume Actual",
                    "Closed Month Volume Target",
                    "Closed Month Volume Achievement",
                    "Closed Month Visit Completion",
                    "Closed Month JP Adherence",
                    "Closed Month Fridge Productivity",
                    "Closed Month Execution Actual",
                    "Closed Month Execution Target",
                    "Closed Month Execution Achievement",
                ]
            ]
        )

    closed_month_table = (
        pd.concat(closed_rows, ignore_index=True)
        if closed_rows
        else pd.DataFrame(
            columns=[
                "Month",
                "Outlet ID",
                "Outlet Name",
                "KA Manager",
                "Segment",
                "Closed Month Volume Actual",
                "Closed Month Volume Target",
                "Closed Month Volume Achievement",
                "Closed Month Visit Completion",
                "Closed Month JP Adherence",
                "Closed Month Fridge Productivity",
                "Closed Month Execution Actual",
                "Closed Month Execution Target",
                "Closed Month Execution Achievement",
            ]
        )
    )

    # Filter values for HTML.
    filters = {
        "datePeriods": [
            {
                "key": "MTD",
                "label": latest_date.strftime("MTD: 1 - %d %b %Y"),
            },
            {
                "key": "YTD",
                "label": latest_date.strftime("YTD: 1 Jan - %d %b %Y"),
            },
        ],
        "kaManagers": sorted(
            outlet["KA Manager"].dropna().unique().tolist()
        ),
        "segments": sorted(
            outlet["Segment"].dropna().unique().tolist()
        ),
        "outlets": (
            outlet[["Outlet ID", "Outlet Name"]]
            .sort_values("Outlet Name")
            .to_dict(orient="records")
        ),
        "skus": sorted(sales["SKU"].dropna().unique().tolist()),
        "categories": sorted(
            set(target["Category"].dropna().unique().tolist())
            | set(sales["Category"].dropna().unique().tolist())
        ),
    }


    # =========================================================
    # DETAILED FACT TABLES FOR INTERACTIVE HTML FILTERING
    # =========================================================
    outlet_filter_dim = outlet[
        [
            "Outlet ID",
            "Outlet Name",
            "KA Manager",
            "Segment",
            "Is Active",
            "Has Fridge",
        ]
    ].copy()

    sales_fact = sales.merge(
        outlet_filter_dim,
        on="Outlet ID",
        how="left",
    )

    target_fact = target.merge(
        outlet_filter_dim[
            ["Outlet ID", "Outlet Name", "KA Manager", "Segment"]
        ],
        on="Outlet ID",
        how="left",
    )

    visit_fact = visit_detail.copy()
    if "Outlet Name" not in visit_fact.columns:
        visit_fact = visit_fact.merge(
            outlet_filter_dim[
                ["Outlet ID", "Outlet Name", "KA Manager", "Segment"]
            ],
            on="Outlet ID",
            how="left",
        )

    execution_fact = execution.merge(
        outlet_filter_dim[
            ["Outlet ID", "Outlet Name", "KA Manager", "Segment"]
        ],
        on="Outlet ID",
        how="left",
    )

    calendar_fact = calendar[["Date", "Is Working Day"]].copy()

    kpi_config_fact = kpi_config[
        ["KPI", "Weight", "Included Final"]
    ].copy()

    payload = {
        "meta": {
            "sourceFile": str(INPUT_FILE),
            "generatedAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lastDataDate": latest_date.strftime("%Y-%m-%d"),
            "currentMonthStart": current_month_start.strftime("%Y-%m-%d"),
            "currentYearStart": current_year_start.strftime("%Y-%m-%d"),
            "elapsedWorkingDays": elapsed_working_days,
            "fullMonthWorkingDays": full_month_working_days,
            "elapsedCalendarDays": mtd_all_days,
            "salesTargetBasis": (
                "Full-month target dated on first day of month; "
                "phased by Calendar_MDM working days only"
            ),
            "fridgeProductivityDayBasis": "All calendar days",
            "targetMonthFallbackUsed": target_fallback_used,
            "targetDateMinimum": (
                target["Target Date"].min().strftime("%Y-%m-%d")
                if not target.empty
                else None
            ),
            "targetDateMaximum": (
                target["Target Date"].max().strftime("%Y-%m-%d")
                if not target.empty
                else None
            ),
            "unmatchedProductRows": unmatched_product_count,
            "productCategoryBasis": (
                "Actual_Sales Product is mapped through Product_MDM to "
                "Bottle/Draught Category. Actual Volume is converted in code to "
                "crate equivalent before dashboard calculations."
            ),
            "crateEquivalentBasis": (
                "Bottle/crate products = 1.0. Keg/draught products = 30L keg / "
                "7.92L bottle crate = 3.787878 crate equivalent."
            ),
            "targetUnitBasis": (
                "Sales_Target Bottle category is treated as crate. Sales_Target Draught category "
                "is treated as keg count and converted to crate equivalent."
            ),
        },
        "filters": filters,
        "kpiTargets": kpi_targets,
        "kpiCards": kpi_cards,
        "charts": {
            "dailyVolume": dataframe_records(daily_sales),
            "managerVolume": dataframe_records(manager_volume),
            "dailyVisits": dataframe_records(daily_visits),
            "managerExecution": dataframe_records(execution_manager),
            "managerFridgeProductivity": dataframe_records(manager_fridge),
            "fridgeBreakdown": dataframe_records(fridge_breakdown),
        },
        "facts": {
            "outlets": dataframe_records(outlet_filter_dim),
            "sales": dataframe_records(sales_fact),
            "targets": dataframe_records(target_fact),
            "visits": dataframe_records(visit_fact),
            "execution": dataframe_records(execution_fact),
            "calendar": dataframe_records(calendar_fact),
            "kpiConfig": dataframe_records(kpi_config_fact),
        },
        "tables": {
            "outletPerformance": dataframe_records(outlet_table),
            "closedMonthByOutlet": dataframe_records(closed_month_table),
            "executionDetail": dataframe_records(execution),
            "visitDetail": dataframe_records(visit_detail),
        },
    }

    # Save outputs.
    OUTPUT_JSON.write_text(
        json.dumps(json_safe(payload), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    outlet_table.to_csv(OUTPUT_OUTLET_CSV, index=False, encoding="utf-8-sig")
    closed_month_table.to_csv(
        OUTPUT_CLOSED_MONTH_CSV,
        index=False,
        encoding="utf-8-sig",
    )
    execution.to_csv(OUTPUT_EXECUTION_CSV, index=False, encoding="utf-8-sig")
    visit_detail.to_csv(OUTPUT_VISIT_CSV, index=False, encoding="utf-8-sig")

    print("\nKA DASHBOARD DATA EXTRACT CREATED")
    print("---------------------------------")
    print(f"Source: {INPUT_FILE}")
    print(f"JSON:   {OUTPUT_JSON}")
    print(f"Outlet: {OUTPUT_OUTLET_CSV}")
    print(f"Closed: {OUTPUT_CLOSED_MONTH_CSV}")
    print(f"Last data date: {latest_date.date()}")
    print(f"KA outlets: {len(outlet):,}")
    print(f"Active outlets: {len(active_outlets):,}")
    print(f"MTD actual: {total_actual:,.0f}")
    print(f"MTD target: {total_target:,.0f}")

    return payload



# =========================================================
# DIRECT EXCEL TO CSV EXPORT
# =========================================================
def _records_to_csv(records, output_file: Path) -> None:
    df = pd.DataFrame(records)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")


def _dict_to_csv(data: dict, output_file: Path) -> None:
    rows = [{"Key": key, "Value": value} for key, value in data.items()]
    pd.DataFrame(rows).to_csv(output_file, index=False, encoding="utf-8-sig")


def export_dashboard_csv() -> Path:
    """
    Direct workflow:
        Excel workbook
            -> this Python file
            -> dashboard_csv/*.csv
            -> HTML / Streamlit

    This does NOT need a second data-builder file.
    """
    CSV_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    payload = build_dashboard_extract()

    facts = payload.get("facts", {})
    meta = payload.get("meta", {})
    filters = payload.get("filters", {})
    kpi_targets = payload.get("kpiTargets", {})

    required_facts = [
        "outlets",
        "sales",
        "targets",
        "visits",
        "execution",
        "calendar",
        "kpiConfig",
    ]

    missing = [name for name in required_facts if name not in facts]
    if missing:
        raise KeyError(
            "Missing required fact tables in build_dashboard_extract output: "
            f"{missing}"
        )

    _records_to_csv(facts["outlets"], CSV_OUTPUT_FOLDER / "outlets.csv")
    _records_to_csv(facts["sales"], CSV_OUTPUT_FOLDER / "sales.csv")
    _records_to_csv(facts["targets"], CSV_OUTPUT_FOLDER / "targets.csv")
    _records_to_csv(facts["visits"], CSV_OUTPUT_FOLDER / "visits.csv")
    _records_to_csv(facts["execution"], CSV_OUTPUT_FOLDER / "execution.csv")
    _records_to_csv(facts["calendar"], CSV_OUTPUT_FOLDER / "calendar.csv")
    _records_to_csv(facts["kpiConfig"], CSV_OUTPUT_FOLDER / "kpi_config.csv")

    _dict_to_csv(meta, CSV_OUTPUT_FOLDER / "meta.csv")
    _dict_to_csv(kpi_targets, CSV_OUTPUT_FOLDER / "kpi_targets.csv")

    # Optional filter files, useful for checking the extract.
    for filter_name, values in filters.items():
        if isinstance(values, list):
            if values and isinstance(values[0], dict):
                pd.DataFrame(values).to_csv(
                    CSV_OUTPUT_FOLDER / f"filter_{filter_name}.csv",
                    index=False,
                    encoding="utf-8-sig",
                )
            else:
                pd.DataFrame({"Value": values}).to_csv(
                    CSV_OUTPUT_FOLDER / f"filter_{filter_name}.csv",
                    index=False,
                    encoding="utf-8-sig",
                )

    print("CSV DASHBOARD EXTRACT CREATED")
    print(f"Excel source: {resolve_input_workbook()}")
    print(f"Output folder: {CSV_OUTPUT_FOLDER}")
    return CSV_OUTPUT_FOLDER



# =========================================================
# DIRECT EXCEL TO SINGLE CSV EXPORT
# =========================================================
SINGLE_CSV_OUTPUT = BASE_FOLDER / "ka_dashboard_extract.csv"


def _clean_records_for_single_csv(records: list[dict], table_name: str) -> pd.DataFrame:
    """Convert one logical table to rows in the single CSV.

    If a table has no rows, we still write one placeholder row with __empty__=1.
    This prevents the HTML/Streamlit loader from thinking the table is missing.
    """
    if not records:
        return pd.DataFrame([{"__table__": table_name, "__empty__": 1}])

    df = pd.DataFrame(records)
    df.insert(0, "__table__", table_name)
    df["__empty__"] = ""
    return df


def _dict_for_single_csv(data: dict, table_name: str) -> pd.DataFrame:
    rows = [
        {"__table__": table_name, "__empty__": "", "Key": key, "Value": value}
        for key, value in data.items()
    ]
    return pd.DataFrame(rows)


def export_dashboard_single_csv(output_file: Path | str | None = None) -> Path:
    """
    Direct workflow:
        Key Accout Report.xlsx
            -> this Python file
            -> ka_dashboard_extract.csv
            -> HTML / Streamlit

    One CSV file is easier to share and easier to ingest in HTML.
    """
    output_path = Path(output_file) if output_file else SINGLE_CSV_OUTPUT

    payload = build_dashboard_extract()

    facts = payload.get("facts", {})
    meta = payload.get("meta", {})
    kpi_targets = payload.get("kpiTargets", {})

    required_facts = [
        "outlets",
        "sales",
        "targets",
        "visits",
        "execution",
        "calendar",
        "kpiConfig",
    ]

    missing = [name for name in required_facts if name not in facts]
    if missing:
        raise KeyError(
            "Missing required fact tables in build_dashboard_extract output: "
            f"{missing}"
        )

    frames = [
        _clean_records_for_single_csv(facts["outlets"], "outlets"),
        _clean_records_for_single_csv(facts["sales"], "sales"),
        _clean_records_for_single_csv(facts["targets"], "targets"),
        _clean_records_for_single_csv(facts["visits"], "visits"),
        _clean_records_for_single_csv(facts["execution"], "execution"),
        _clean_records_for_single_csv(facts["calendar"], "calendar"),
        _clean_records_for_single_csv(facts["kpiConfig"], "kpiConfig"),
        _dict_for_single_csv(meta, "meta"),
        _dict_for_single_csv(kpi_targets, "kpiTargets"),
    ]

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.replace([float("inf"), float("-inf")], pd.NA)
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("SINGLE CSV DASHBOARD EXTRACT CREATED")
    print(f"Excel source: {resolve_input_workbook()}")
    print(f"Output file: {output_path}")
    return output_path


if __name__ == "__main__":
    export_dashboard_single_csv()
