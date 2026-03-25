# Actuarial Reserving Method Reference

## Key Concepts

### Triangle Structure
A loss development triangle has:
- **Rows** = accident periods (years, quarters, etc.)
- **Columns** = development ages (months since start of period)
- **Upper-left triangle** = observed data
- **Lower-right triangle** = future development to be projected

### Age-to-Age Factor (ATA / LDF)
The ratio of cumulative losses at age N+1 to cumulative losses at age N, for a given accident period.
`LDF(12→24, AY2020) = Value(AY2020, 24) / Value(AY2020, 12)`

### Cumulative Development Factor (CDF)
The product of all selected ATAs from a given age to ultimate (including the tail).
`CDF(12) = LDF(12→24) × LDF(24→36) × ... × LDF(108→120) × Tail`

### Percent Developed
The fraction of the ultimate that has already emerged at a given age.
`% Developed = 1 / CDF`

### Tail Factor
The CDF from the oldest observed age to true ultimate. Should be ≥ 1.000.
A tail of 1.000 means all development is assumed complete at the oldest age.

---

## Chain Ladder Method

**Concept:** Project each accident period's losses forward from its current age to ultimate by multiplying the actual losses by the CDF at the current age.

```
CL Ultimate = Actual × CDF(current age)
CL IBNR     = CL Ultimate − Actual
```

**Agent's job:** Select one LDF for each development interval (and the tail) from among the computed averages, based on stability, trend, and credibility.

**Selection guidance:**
- **Low CV, flat slope** → use weighted all-year average (most credible)
- **Upward trend** → prefer recent-year weighted average (3yr or 5yr)
- **Downward trend** → consider all-year or medial (exclude-high-low) average
- **Sparse data (2–3 points)** → use simple average; note low credibility
- **Tail** → must be ≥ 1.000; set to 1.000 only if the oldest AY is fully developed

---

## Initial Expected Method

**Concept:** The reserve estimate equals a pre-determined expected ultimate loss (or ELR × premium) minus what has already been paid/incurred.

```
IE Ultimate = Expected Ultimate (provided externally)
IE IBNR     = IE Ultimate − Actual
```

**No agent selection required.** The inputs are provided by the user.

**When it's useful:** Early accident periods where actual data is too sparse to be credible; as the "prior" in BF.

---

## Bornhuetter-Ferguson Method

**Concept:** BF blends the chain-ladder and initial-expected methods. The credibility weight given to actual data equals the % developed (how much of the ultimate has emerged), and the weight on the initial expected is 1 minus that.

```
BF Ultimate = (% Developed × Actual) + ((1 − % Developed) × Expected Ultimate)
            = Actual + (1 − % Developed) × Expected Ultimate

BF IBNR     = (1 − % Developed) × Expected Ultimate
```

For a fully developed period (% Developed = 1.0), BF = Chain Ladder.
For a brand-new period (% Developed = 0.0), BF = Initial Expected.

**No agent selection required.** BF is fully determined by the CL selections (which drive % developed) and the IE inputs.

---

## Comparing the Three Methods

| Period maturity | Chain Ladder reliability | BF blend toward |
|-----------------|--------------------------|-----------------|
| Very immature (12 mo) | Low — few data points | IE (high weight on a priori) |
| Moderately mature (36–60 mo) | Medium | Mix of both |
| Mature (72+ mo) | High | CL (actual data dominates) |

A common approach is to:
1. Use BF for immature periods (first 2–3 years of a 10-year triangle)
2. Use Chain Ladder for more mature periods
3. Average or select between methods for the middle range

---

## Output File Reference

| File | Contents |
|------|----------|
| `output/prep/triangles.csv` | Normalized long-format triangle data |
| `output/prep/diagonal.csv` | Latest observation per period × measure |
| `output/prep/ldf_averages.csv` | LDF averages by interval × measure |
| `output/selections/cl_selections.json` | Agent's LDF selections |
| `output/selections/ie_inputs.json` | User-provided initial expected inputs |
| `output/chain-ladder/cl_ultimates.csv` | CL ultimate by period × measure |
| `output/initial-expected/ie_ultimates.csv` | IE ultimate by period × measure |
| `output/bornhuetter-ferguson/bf_ultimates.csv` | BF ultimate by period × measure |
| `output/combined_ultimates.csv` | All three methods side by side |
