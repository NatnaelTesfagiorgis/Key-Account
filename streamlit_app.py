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


def dataframe_to_payload(df: pd.DataFrame) -> dict:
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


def load_payload_from_path(csv_path: Path) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV extract was not found: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    return dataframe_to_payload(df)


def load_payload_from_upload(uploaded_file) -> dict:
    df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    return dataframe_to_payload(df)


def render_dashboard(payload: dict) -> None:
    html = HTML_FILE.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    injection = f"""
<script>
(function(){{
  const payload = {payload_json};
  function boot() {{
    if (typeof init === 'function') {{
      init(payload);
    }} else {{
      document.body.insertAdjacentHTML('afterbegin',
        '<div style="padding:20px;color:#b00020;font-weight:800">Dashboard init() was not found in HTML.</div>');
    }}
  }}
  if (document.readyState === 'loading') {{
    window.addEventListener('DOMContentLoaded', boot);
  }} else {{
    boot();
  }}
}})();
</script>
"""
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

dashboard_slot = st.empty()

st.divider()
st.markdown("### Data File Loader")
st.caption("This loader is at the bottom. Upload `ka_dashboard_extract.csv`, or leave it blank to use the file in the same folder.")

uploaded = st.file_uploader("Upload ka_dashboard_extract.csv", type=["csv"])
csv_path_text = st.text_input("Default CSV path", value=str(DEFAULT_CSV_FILE))
load_button = st.button("Load / Refresh", use_container_width=False)

payload = None
load_source = None

try:
    if uploaded is not None:
        payload = load_payload_from_upload(uploaded)
        load_source = f"uploaded file: {uploaded.name}"
    else:
        payload = load_payload_from_path(Path(csv_path_text))
        load_source = f"default file: {csv_path_text}"

    with dashboard_slot.container():
        render_dashboard(payload)

    st.success(f"Dashboard loaded from {load_source}.")
except Exception as exc:
    with dashboard_slot.container():
        st.error("Dashboard could not be loaded.")
        st.exception(exc)
    st.warning("Upload the latest `ka_dashboard_extract.csv` using the Data File Loader below.")
