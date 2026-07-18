# KA Dashboard v22 - Clean Upload + Draught Target Fix

This is a clean complete package.

What is fixed:
- CSV upload/population fixed using the working Streamlit app.
- SKU filter removed.
- Top Outlet filter removed.
- Outlet selector remains only in Outlet Vol. Perf. table.
- Active month appears only as MTD.
- Category matching is trimmed and case-insensitive.
- Category dropdown is built from both Sales and Targets.
- Visuals trust the extract values:
  - Actual Volume
  - Full Month Target
- No extra visual-layer re-conversion is applied.

For Netsanet / Employee ID 215:
- Select Category = Draught.
- Expected card:
  - Actual around 1,273
  - Target around 1,000 for MTD, if elapsed/full working days are 12/23.
- If Category = ALL, the target includes Bottle + Draught.
