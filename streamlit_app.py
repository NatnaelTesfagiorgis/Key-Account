from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


BASE_FOLDER = Path(__file__).resolve().parent
DEFAULT_CSV_FILE = BASE_FOLDER / "ka_dashboard_extract.csv"
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

    return {
        "facts": facts,
        "meta": meta,
        "kpiTargets": kpi_targets,
    }


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

    components.html(html, height=2800, scrolling=True)


st.set_page_config(
    page_title="KA Performance Dashboard",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="expanded",
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

with st.sidebar:
    st.title("KA Dashboard")
    st.caption("Single CSV version")

    csv_file_input = st.text_input(
        "CSV file path",
        value=str(DEFAULT_CSV_FILE),
        help="This should point to ka_dashboard_extract.csv",
    )

    uploaded = st.file_uploader(
        "Or upload ka_dashboard_extract.csv",
        type=["csv"],
    )

    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


try:
    if uploaded is not None:
        temp_file = BASE_FOLDER / "_uploaded_ka_dashboard_extract.csv"
        temp_file.write_bytes(uploaded.getvalue())
        payload = load_payload(str(temp_file))
    else:
        payload = load_payload(csv_file_input)

    render_dashboard(payload)

except Exception as exc:
    st.error("Dashboard could not be loaded from the single CSV.")
    st.exception(exc)
