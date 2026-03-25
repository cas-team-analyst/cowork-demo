---
name: chain-ladder
description: >
  Chain-ladder LDF selection step. Use when performing chain-ladder development,
  selecting age-to-age factors, or making LDF selections for actuarial reserving.
---

# Chain Ladder — LDF Selection

## What You Do

Read `output/prep/ldf_averages.csv` and select an age-to-age factor (LDF) for
each (measure × interval) combination. Then write `output/selections/cl_selections.json`.

Run script 4 after writing the JSON:
```bash
python scripts/4-apply-cl-selections.py
```
Output: `output/chain-ladder/chain-ladder.xlsx`

## Reading the LDF Averages

Open or read `output/prep/ldf_averages.csv`. Columns:
- `measure` — triangle measure (e.g. "Incurred Loss", "Paid Loss")
- `interval` — development interval (e.g. "12-24", "96-108")
- `weighted_all`, `simple_all`, `excl_hi_lo_all` — full-history averages
- `weighted_3yr`, `simple_3yr`, `excl_hi_lo_3yr` — recent 3-year averages
- `weighted_5yr`, `simple_5yr`, `excl_hi_lo_5yr` — recent 5-year averages
- `cv_3yr`, `cv_5yr` — coefficient of variation (stability measure)
- `slope_3yr`, `slope_5yr` — trend in recent LDFs (positive = rising)

## Selection Principles

For each interval, choose one LDF based on:
1. **Stability** — prefer low CV; if `cv_3yr < 0.02`, simple averages are reliable
2. **Recent trend** — if `slope_3yr` is significantly positive/negative, weight toward recent years
3. **Sparse data** — for the oldest intervals (few data points), use `weighted_all` or `simple_all`
4. **Tail** — apply a tail factor for development beyond the oldest age; default = 1.000 if the oldest interval's LDF is already near 1.0

## Selections JSON Format

Write to `output/selections/cl_selections.json`:
```json
[
  {
    "measure": "Incurred Loss",
    "interval": "12-24",
    "selected_ldf": 1.8093,
    "reasoning": "Weighted 3-year average selected; low CV (0.012) indicates stable development."
  },
  {
    "measure": "Incurred Loss",
    "interval": "tail",
    "selected_ldf": 1.0000,
    "reasoning": "Oldest interval LDF is 1.005; tail set to 1.000 assuming no further development."
  },
  ...
]
```

Required fields: `measure`, `interval`, `selected_ldf`, `reasoning`
- Include one entry per (measure × interval) — don't skip any intervals
- Include one `"tail"` entry per measure
- Measure names must match exactly as they appear in `ldf_averages.csv`
