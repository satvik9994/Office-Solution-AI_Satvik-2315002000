# Automated BI Migration Accuracy Engine - Benchmark Report

## 1. Executive Summary Table

| Metric Category | Baseline (Before) | Engine (After) | Improvement | Evidence |
| :--- | ---: | ---: | ---: | :--- |
| **DAX Structural Accuracy** | **0.0%** | **100.0%** | **+100.0%** | 0/3 -> 3/3 verifiable formulas |
| **Numerical Agreement Rate** | **0.0%** | **100.0%** | **+100.0%** | 0/3 baseline; 3/3 engine |
| **Visual Mapping Accuracy** | N/A | **100.0%** | **+100.0%** | 2/2 matches |
| **Flaw Detection Sensitivity** | N/A | **100.0%** | N/A | 4/4 labelled flaws detected |
| **Correction Success Rate** | N/A | **75.0%** | N/A | 3/4 fully verified corrections |
| **Mean Calibrated Confidence** | 0.3 | **0.82** | **+0.52** | Mean over 4 calculations |

### Metric Integrity Note

- `1` ground-truth item(s) contain an incomplete template (`...`) and are excluded from structural/numerical certification metrics.
- A correction is counted as successful only when the generated formula is structurally verified and its numerical validation is also verified where numerical validation is available.
- No baseline metric is hard-coded; baseline values come from the supplied legacy DAX and numerical validation results.

## 2. Before-vs-After Item Comparison

| ID | Name | Baseline Structural | Engine Structural | Baseline Numerical | Engine Numerical | Correction Status | Confidence |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `calc_1` | Profit_Ratio | FAIL | PASS | MISMATCH | VERIFIED | VERIFIED | 1.0 |
| `calc_2` | Region_Sales | FAIL | PASS | MISMATCH | VERIFIED | VERIFIED | 0.98 |
| `calc_3` | Advanced_KPI | FAIL | N/A | UNSUPPORTED | UNSUPPORTED | UNVERIFIABLE | 0.3 |
| `calc_4` | Sales_Category | FAIL | PASS | MISMATCH | VERIFIED | VERIFIED | 1.0 |

## 3. Visual Mapping Benchmark

| Visual ID | Tableau Visual | Confidence | Predicted Power BI Visual | Target | Match? |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `vis_1` | `bar` | 0.95 | **`clustered column chart`** | `clustered column chart` | PASS |
| `vis_2` | `line` | 0.98 | **`line chart`** | `line chart` | PASS |
