"""
Script 5: Apply the Initial Expected (IE) method.

Reads CL ultimates (from script 4) plus user-provided IE inputs, then writes
canonical Excel output showing CL context, selected IE ultimate, IBNR, and Unpaid.

Usage (run from the project root):
    python scripts/5-apply-ie.py

Inputs:
    output/prep/diagonal.pkl
    output/chain-ladder/cl_ultimates.csv
    output/selections/ie_inputs.json

ie_inputs.json format (two supported styles):

  Style A - direct ultimate by period and measure:
    [
      {"period": "2015", "measure": "Incurred Loss", "expected_ultimate": 45000000},
      ...
    ]

  Style B - expected loss ratio applied to premium:
    [
      {"period": "2015", "measure": "Incurred Loss", "elr": 0.72, "premium": 62500000},
      ...
    ]

Outputs:
    output/initial-expected/
        initial-expected.xlsx   (canonical format: Loss sheet + Counts sheet)
        ie_ultimates.csv        (internal: expected ultimates per period x measure)
    output/inputs/
        ie_inputs.json          (copy of inputs for reference)
"""

import pandas as pd
import numpy as np
import json
import os
import shutil


def _try_int(series):
    """Convert series to int if all values are numeric, else return as-is."""
    try:
        return series.astype(str).apply(lambda x: int(float(x)))
    except (ValueError, TypeError):
        return series.astype(str)


INPUT_DIAGONAL   = "output/prep/diagonal.pkl"
INPUT_CL_ULTS    = "output/chain-ladder/cl_ultimates.csv"
IE_INPUTS_JSON   = "output/selections/ie_inputs.json"
OUTPUT_DIR       = "output/initial-expected"
OUTPUT_INPUTS    = "output/inputs"

# Unpaid = Ultimate(this measure) - diagonal(proxy measure)
UNPAID_PROXY = {
    "Incurred Loss":  "Paid Loss",
    "Paid Loss":      "Paid Loss",
    "Reported Count": "Closed Count",
    "Closed Count":   "Closed Count",
}


def load_ie_inputs(path):
    with open(path) as f:
        data = json.load(f)
    rows = []
    for item in data:
        if "expected_ultimate" in item:
            rows.append(dict(period=str(item["period"]), measure=str(item["measure"]),
                             expected_ultimate=float(item["expected_ultimate"])))
        elif "elr" in item and "premium" in item:
            rows.append(dict(period=str(item["period"]), measure=str(item["measure"]),
                             expected_ultimate=float(item["elr"]) * float(item["premium"])))
        else:
            raise ValueError(f"ie_inputs.json entry missing 'expected_ultimate' or 'elr'+'premium': {item}")
    return pd.DataFrame(rows)


def build_ie_results(diag, cl_ults, ie_df):
    """Merge diagonal, CL ultimates, and IE inputs into one result DataFrame."""
    diag = diag.copy()
    diag["period"]  = diag["period"].astype(str)
    diag["measure"] = diag["measure"].astype(str)
    diag["age"]     = diag["age"].astype(str)

    cl_wide = cl_ults.pivot_table(index="period", columns="measure",
                                  values="cl_ultimate", aggfunc="first")

    results = []
    for _, r in diag.iterrows():
        period  = r["period"]
        measure = r["measure"]
        actual  = r["value"]

        ie_row = ie_df[(ie_df["period"] == period) & (ie_df["measure"] == measure)]
        ie_ult = float(ie_row["expected_ultimate"].iloc[0]) if not ie_row.empty else np.nan

        # CL ultimates for the two sibling measures (Incurred+Paid or Reported+Closed)
        cl_inc = cl_wide.get("Incurred Loss", {}).get(period, np.nan)
        cl_paid= cl_wide.get("Paid Loss",     {}).get(period, np.nan)
        cl_rep = cl_wide.get("Reported Count",{}).get(period, np.nan)
        cl_cls = cl_wide.get("Closed Count",  {}).get(period, np.nan)

        proxy_measure = UNPAID_PROXY.get(measure)
        proxy_actual  = diag[diag["measure"] == proxy_measure]
        proxy_actual  = proxy_actual[proxy_actual["period"] == period]
        proxy_val     = float(proxy_actual["value"].iloc[0]) if not proxy_actual.empty else actual

        ibnr   = (ie_ult - actual)     if pd.notna(ie_ult) else np.nan
        unpaid = (ie_ult - proxy_val)  if pd.notna(ie_ult) else np.nan

        results.append(dict(
            period       = period,
            measure      = measure,
            current_age  = r["age"],
            actual       = round(actual, 2),
            cl_incurred  = cl_inc,
            cl_paid      = cl_paid,
            cl_reported  = cl_rep,
            cl_closed    = cl_cls,
            ie_ultimate  = round(ie_ult, 2) if pd.notna(ie_ult) else np.nan,
            ie_ibnr      = round(ibnr,   2) if pd.notna(ibnr)   else np.nan,
            ie_unpaid    = round(unpaid, 2) if pd.notna(unpaid)  else np.nan,
        ))

    return pd.DataFrame(results)


def exposure_for_periods(diag):
    """Extract the latest exposure value per period."""
    exp = diag[diag["measure"] == "Exposure"].copy()
    if exp.empty:
        return {}
    exp["age_int"] = _try_int(exp["age"])
    latest = exp.sort_values("age_int").groupby("period").last()
    return latest["value"].to_dict()


def write_ie_excel(results, exp_by_period, path):
    """Write canonical initial-expected Excel: Loss sheet + Counts sheet."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # ── Loss sheet (Incurred Loss) ──────────────────────────────────────
        loss_measures = ["Incurred Loss", "Paid Loss"]
        loss = results[results["measure"].isin(loss_measures)].copy()

        inc = loss[loss["measure"] == "Incurred Loss"].set_index("period")
        paid= loss[loss["measure"] == "Paid Loss"].set_index("period")
        if not inc.empty:
            out_loss = pd.DataFrame({
                "Accident Period":    _try_int(inc.index.to_series()),
                "Current Age":        _try_int(inc["current_age"]),
                "Exposure":           [exp_by_period.get(p, np.nan) for p in inc.index],
                "CL Ultimate Incurred": inc["cl_incurred"],
                "CL Ultimate Paid":     inc["cl_paid"],
                "CL Ultimate":          ((inc["cl_incurred"].fillna(0) + inc["cl_paid"].fillna(0)) / 2
                                         ).where(inc["cl_incurred"].notna() | inc["cl_paid"].notna()),
                "Selected Ultimate Loss": inc["ie_ultimate"],
                "IBNR":               inc["ie_ibnr"],
                "Unpaid":             inc["ie_unpaid"],
            })
            out_loss.to_excel(writer, sheet_name="Loss", index=False)

        # ── Counts sheet (Reported Count) ───────────────────────────────────
        count_measures = ["Reported Count", "Closed Count"]
        counts = results[results["measure"].isin(count_measures)].copy()

        rep = counts[counts["measure"] == "Reported Count"].set_index("period")
        cls = counts[counts["measure"] == "Closed Count"].set_index("period")
        if not rep.empty:
            out_counts = pd.DataFrame({
                "Accident Period":      _try_int(rep.index.to_series()),
                "Current Age":          _try_int(rep["current_age"]),
                "Exposure":             [exp_by_period.get(p, np.nan) for p in rep.index],
                "CL Ultimate Reported": rep["cl_reported"],
                "CL Ultimate Closed":   rep["cl_closed"],
                "CL Ultimate":          ((rep["cl_reported"].fillna(0) + rep["cl_closed"].fillna(0)) / 2
                                         ).where(rep["cl_reported"].notna() | rep["cl_closed"].notna()),
                "Selected Counts":      rep["ie_ultimate"],
                "IBNR":                 rep["ie_ibnr"],
                "Unpaid":               rep["ie_unpaid"],
            })
            out_counts.to_excel(writer, sheet_name="Counts", index=False)

    print(f"  Saved -> {path}")


def main():
    os.makedirs(OUTPUT_DIR,    exist_ok=True)
    os.makedirs(OUTPUT_INPUTS, exist_ok=True)

    diag    = pd.read_pickle(INPUT_DIAGONAL)
    diag["period"]  = diag["period"].astype(str)
    diag["measure"] = diag["measure"].astype(str)
    diag["age"]     = diag["age"].astype(str)

    cl_ults = pd.read_csv(INPUT_CL_ULTS)
    cl_ults["period"]  = cl_ults["period"].astype(str)
    cl_ults["measure"] = cl_ults["measure"].astype(str)

    ie_df = load_ie_inputs(IE_INPUTS_JSON)
    print(f"Loaded {len(ie_df)} IE input entries")

    exp_by_period = exposure_for_periods(diag)
    results       = build_ie_results(diag, cl_ults, ie_df)

    # Save internal CSV
    ie_out = results[["period","measure","current_age","actual","ie_ultimate","ie_ibnr","ie_unpaid"]].copy()
    ie_out.columns = ["period","measure","current_age","actual","expected_ultimate","ie_ibnr","ie_unpaid"]
    ie_out.to_csv(f"{OUTPUT_DIR}/ie_ultimates.csv", index=False)

    write_ie_excel(results, exp_by_period, f"{OUTPUT_DIR}/initial-expected.xlsx")
    shutil.copy2(IE_INPUTS_JSON, f"{OUTPUT_INPUTS}/ie_inputs.json")

    print("\nIE summary by measure:")
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    for m in results["measure"].unique():
        sub = results[results["measure"] == m]
        if sub["ie_ultimate"].isna().all():
            continue
        print(f"  {m}: Actual={sub['actual'].sum():,.0f}  "
              f"IE Ultimate={sub['ie_ultimate'].sum():,.0f}  "
              f"IBNR={sub['ie_ibnr'].sum():,.0f}")

    print(f"  Saved -> {OUTPUT_DIR}/ie_ultimates.csv, initial-expected.xlsx")


if __name__ == "__main__":
    print("=== Step 5: Applying Initial Expected method ===")
    main()
