# KA Dashboard v25 - Draught Displayed in Keg

This version keeps the extract and KPI calculations in crate equivalent, but changes the visual display:

- If Category = Draught:
  - Actual, Target, Daily Target, Run Rate, Variance, and Volume charts are displayed in Keg.
  - Achievement percentages stay the same because both actual and target are divided by the same keg factor.
- If Category = Bottle or ALL:
  - Volumes are displayed in crate equivalent.

Keg factor:
- 1 keg = 30L
- 1 bottle crate = 24 × 0.33L = 7.92L
- 1 keg = 30 / 7.92 = 3.787878 crate equivalent

Example for Netsanet / Employee ID 215:
- Draught MTD actual 1,272.73 crate equivalent displays as 336 kegs.
- Draught MTD target 1,000 crate equivalent displays as 264 kegs.
- Achievement remains about 127%.
