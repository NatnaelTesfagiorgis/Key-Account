from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


BASE_FOLDER = Path(__file__).resolve().parent
DEFAULT_CSV_FILE = BASE_FOLDER / "ka_dashboard_extract.csv"
UPLOADED_CSV_FILE = BASE_FOLDER / "_uploaded_ka_dashboard_extract.csv"
HTML_FILE = BASE_FOLDER / "KA_Dashboard_Single_CSV_Loader.html"


def clean_record(record: dict) -> dict:
    return {
        key: value
        for key, value in record.items()
        if key not in {"__table__", "__empty__"} and pd.notna(value) and str(value) != ""
    }


@st.cache_data(show_spinner="Loading single CSV dashboard data...")
def load_payload(csv_file_text: str) -> dict:
    csv_file = Path(csv_file_text)

    if not csv_file.exists():
        raise FileNotFoundError(f"CSV extract was not found: {csv_file}")

    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    if "__table__" not in df.columns:
        raise KeyError("CSV must contain a '__table__' column.")

    facts = {
        "outlets": [],
        "sales": [],
        "targets": [],
        "visits": [],
        "execution": [],
        "calendar": [],
        "kpiConfig": [],
    }
    meta = {}
    kpi_targets = {}
    seen_tables = set()

    for row in df.to_dict("records"):
        table_name = str(row.get("__table__", "")).strip()
        if table_name:
            seen_tables.add(table_name)

        if table_name in facts:
            if str(row.get("__empty__", "")).strip() == "1":
                continue
            facts[table_name].append(clean_record(row))
        elif table_name == "meta" and pd.notna(row.get("Key")):
            meta[str(row["Key"])] = row.get("Value")
        elif table_name == "kpiTargets" and pd.notna(row.get("Key")):
            value = row.get("Value")
            try:
                value = float(value)
            except Exception:
                pass
            kpi_targets[str(row["Key"])] = value

    missing = [name for name in facts if name not in seen_tables]
    if missing:
        raise ValueError("Missing table section in CSV: " + ", ".join(missing))

    return {"facts": facts, "meta": meta, "kpiTargets": kpi_targets}


def render_dashboard(payload: dict) -> None:
    html = HTML_FILE.read_text(encoding="utf-8")

    injection = (
        "<script>\n"
        "window.addEventListener('load', function(){\n"
        f"  const payload = {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))};\n"
        "  if (typeof init === 'function') { init(payload); }\n"
        "});\n"
        "</script>\n"
    )
    html = html.replace("</body>", injection + "</body>")
    components.html(html, height=2850, scrolling=True)


st.set_page_config(
    page_title="KA Performance Dashboard",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {padding-top:0.4rem;padding-left:0.7rem;padding-right:0.7rem;max-width:100%;}
    header[data-testid="stHeader"] {background: transparent;}
    #MainMenu, footer {visibility:hidden;}
    iframe {border:0;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "csv_file_path" not in st.session_state:
    st.session_state.csv_file_path = str(DEFAULT_CSV_FILE)

load_error = None
try:
    payload = load_payload(st.session_state.csv_file_path)
    render_dashboard(payload)
except Exception as exc:
    load_error = exc
    st.error("Dashboard could not be loaded from the single CSV.")
    st.exception(exc)

st.divider()
st.markdown("### Data File Loader")
st.caption("The loader is now at the bottom. The dashboard loads from `ka_dashboard_extract.csv` by default.")

csv_file_input = st.text_input(
    "CSV file path",
    value=st.session_state.csv_file_path,
    help="This should point to ka_dashboard_extract.csv",
)

uploaded = st.file_uploader(
    "Or upload ka_dashboard_extract.csv",
    type=["csv"],
)

col1, col2 = st.columns([1, 5])
with col1:
    refresh_clicked = st.button("Refresh / Load", use_container_width=True)

if uploaded is not None:
    UPLOADED_CSV_FILE.write_bytes(uploaded.getvalue())
    st.session_state.csv_file_path = str(UPLOADED_CSV_FILE)
    st.cache_data.clear()
    st.rerun()

if refresh_clicked:
    st.session_state.csv_file_path = csv_file_input
    st.cache_data.clear()
    st.rerun()
