# Automated BI Migration Accuracy Engine

An explainable, deterministic compiler and validation engine designed to automate the translation, validation, and error correction of Business Intelligence assets during Tableau-to-Power BI migrations.

---

## 1. Problem Statement & Objective

Migrating enterprise BI environments from Tableau to Power BI is historically error-prone, labor-intensive, and fraught with semantic inaccuracies. Legacy migration scripts typically rely on shallow regular expressions or naive string replacements that fail on:
* **Nested & Compound Logic:** Breaking operator precedence and paren nesting.
* **Level of Detail (LOD) Expressions:** Dropping fixed dimensional scoping.
* **Table Calculations:** Hallucinating translations without visual shelf context.
* **Inverted / Unsafe Formulas:** Generating division operations that crash on zero denominators or swap numerators and denominators.
* **Return Type Violations:** Coercing text categories (`"High"`, `"Low"`) into numbers (`1`, `0`).

### Primary Objectives:
1. Parse and compile Tableau calculations (JSON and XML) into idiomatic, safe Power BI DAX.
2. Resolve multi-step dependent calculation pipelines using a Directed Acyclic Graph (DAG) and topological sorting.
3. Ingest legacy flawed DAX conversions, diagnose their specific failure modes, and generate corrected candidates.
4. Execute empirical numerical validation on sample tabular data (`sample_data.csv`).
5. Map Tableau visual marks to Power BI visual archetypes with explainable confidence.
6. Provide calibrated, transparent multi-factor confidence scores.
7. Benchmark before-vs-after accuracy improvements across standardized metrics.

---

## 2. Input Data & Artifact Schemas

The engine ingests the following artifact types:
* **Tableau Calculations (`data/tableau_calculations.json`):** 4 core test calculations including simple division (`Profit_Ratio`), Level of Detail (`Region_Sales`), nested compound conditionals (`Advanced_KPI`), and categorical logic (`Sales_Category`).
* **Calculation Dependencies (`data/tableau_dependencies.json`):** Multi-step pipeline (`Step1` → `Step2` → `FinalMetric`).
* **Tableau Workbook XML (`data/tableau_xml.xml`):** XML-embedded table calculations (`RunningSales`, `RankSales`).
* **Flawed Baseline Conversions (`data/incorrect_dax.json`):** Benchmark legacy conversions exhibiting inverted ratios, stripped LODs, truncated logic, and mutated return types.
* **Ground Truth Benchmarks (`data/ground_truth.json`):** Certified target DAX formulas.
* **Visual Metadata (`data/visuals.json`):** Mark types, dimensional axes, and measures.
* **Tabular Datasets (`data/sample_data.csv`, `data/sample_data.xlsx`):** 5-row dimensional fact table containing `Region`, `Sales`, `Profit`, `Cost`, and `Date`.

---

## 3. Project Structure

```
project/
├── data/                              # Company-provided input data
│   ├── tableau_calculations.json      # 4 Tableau calculated fields
│   ├── tableau_dependencies.json      # 3-step dependent calculation chain
│   ├── tableau_xml.xml                # XML-embedded table calculations
│   ├── incorrect_dax.json             # 4 flawed legacy DAX conversions
│   ├── ground_truth.json              # 4 certified correct DAX targets
│   ├── visuals.json                   # 2 visual mapping definitions
│   ├── sample_data.csv                # 5-row fact table for validation
│   └── sample_data.xlsx               # Same data in Excel format
├── src/
│   ├── ingestion/
│   │   ├── file_reader.py             # BOM-safe JSON/XML/CSV/XLSX loader
│   │   └── models.py                  # Domain dataclasses
│   ├── parser/
│   │   ├── tokens.py                  # Token type definitions
│   │   ├── lexer.py                   # Character-level Tableau tokenizer
│   │   └── parser.py                  # Recursive-descent parser → IR
│   ├── ir/
│   │   └── ir_nodes.py                # Intermediate Representation nodes
│   ├── resolver/
│   │   └── dependency_graph.py        # Kahn's topological sort + cycle detection
│   ├── translator/
│   │   └── dax_emitter.py             # IR tree → DAX code generation
│   ├── validation/
│   │   ├── error_detector.py          # Flaw categorization engine
│   │   └── numerical_engine.py        # Pandas-based formula validation
│   ├── visual_mapping/
│   │   └── visual_mapper.py           # Visual type + context mapper
│   ├── intelligence/
│   │   └── scorer.py                  # 4-pillar confidence scoring
│   └── evaluation/
│       ├── metrics.py                 # Before-vs-after benchmark calculator
│       └── reporter.py                # JSON + Markdown output generator
├── tests/
│   ├── test_ingestion.py              # File loading tests (6 tests)
│   ├── test_resolver.py               # Dependency resolution tests (9 tests)
│   ├── test_parser_and_ir.py          # Lexer/parser/IR tests (18 tests)
│   ├── test_emitter.py                # DAX code generation tests (11 tests)
│   ├── test_validation.py             # Error detection + numerical tests (11 tests)
│   ├── test_visual_and_scorer.py      # Visual mapping + confidence tests (18 tests)
│   └── test_end_to_end.py             # Integration pipeline tests (9 tests)
├── output/                            # Generated outputs (created by main.py)
│   ├── migration_results.json         # Primary output per company schema
│   ├── benchmark_report.md            # Markdown before-vs-after report
│   ├── error_analysis.json            # Detailed error analysis per calc
│   ├── dependency_chain_results.json  # Multi-step dependency DAX translations
│   └── xml_table_calc_results.json    # XML table calculation DAX translations
├── main.py                            # Pipeline orchestrator entry point
├── run_all_tests.py                   # Master test runner
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
└── README.md                          # This documentation
```

---

## 4. Modular System Architecture

The engine is engineered as a deterministic compiler and validation harness:

```
[Raw Files]
     │ (JSON / XML / CSV / XLSX)
     ▼
[Module 1: Ingestion & Normalizer] (BOM removal, CSV unquoting, schema standardization)
     │
     ▼
[Module 2: Dependency Resolver] (Kahn's DAG topological sorting, cycle detection)
     │
     ▼
[Module 3: Lexer & Recursive-Descent Parser] (Formal grammar, operator precedence)
     │
     ▼
[Module 4: Intermediate Representation (IR)] (Semantic tree nodes)
     │
     ▼
[Module 5: DAX Emitter] (Safe DIVIDE, ALLEXCEPT, ALLSELECTED, Table[Col] vs [Measure])
     │
     ├─────────────────────────────────────────┐
     ▼                                         ▼
[Module 6: Error Detector]            [Module 8: Visual Mapper]
     │ (Diagnoses legacy flaws)                │ (Maps visual archetypes & feeds context)
     ▼                                         │
[Module 7: Numerical Engine]                   │
     │ (Pandas simulation on sample_data.csv)  │
     └────────────────────┬────────────────────┘
                          ▼
            [Module 9: Confidence Scorer]
                          │ (4-pillar calibrated scoring)
                          ▼
            [Module 10: Evaluation & Reporter]
                          │
     ┌────────────────────┼────────────────────┐
     ▼                    ▼                    ▼
migration_results.json  benchmark_report.md  error_analysis.json
                    dependency_chain_results.json
                    xml_table_calc_results.json
```

---

## 5. Key Engineering Modules

### 5.1. Intermediate Representation (IR)
Rather than fragile regex replacements, the engine compiles formulas into an explicit, language-agnostic Intermediate Representation (`src/ir/ir_nodes.py`):
* `IRBinaryOp(DIVIDE, ...)`: Enforces conversion of `/` into DAX `DIVIDE()`.
* `IRLODExpression(FIXED, dims, agg)`: Encapsulates dimensional scoping.
* `IRConditional(cond, then, else)`: Recursively models nested `IF...THEN...ELSE` blocks.
* `IRTableCalculation(RUNNING_SUM, inner, order_by)`: Decorates window calculations with axis context.
* `IRUnsupportedFunction(name, args)`: Fallback for unknown functions with confidence penalty.

**Why IR over simple string replacement:**
String replacement cannot handle operator precedence (`A / B - C` vs `A / (B - C)`), nested parentheses, or context-dependent translations (LOD → CALCULATE). The IR preserves the semantic tree structure so the DAX emitter can make safe, structural decisions.

### 5.2. Multi-Step Dependency Resolution (DAG Engine)
* **Identifier Separation:** Regex extracts bracketed tokens `[Token]`. Physical dataset columns (`Sales`, `Cost`) are filtered out; remaining tokens are matched case-insensitively against registered calculations.
* **Topological Sort:** Employs Kahn's algorithm (O(V+E)). Calculations can be ingested in completely scrambled order and are executed deterministically.
* **Cycle Trap:** Circular dependencies (A → B → A) are trapped before code generation, raising `CircularDependencyError` and assigning 0.0 confidence.
* **Missing Dependency Trap:** References to unknown fields/calculations raise `MissingDependencyError`.

### 5.3. Tableau → DAX Translation Rules
* **Safe Division:** `A / B` → `DIVIDE(A, B)`
* **String Literals:** `'Text'` → `"Text"` (DAX requires double quotes)
* **Level of Detail (FIXED):**
  `{FIXED [D]: AGG([M])}` → `CALCULATE(AGG(Table[M]), ALLEXCEPT(Table, Table[D]))`
* **Table Calculations:**
  * `WINDOW_SUM(expr)` → `CALCULATE(expr, ALLSELECTED(Table))`
  * `RUNNING_SUM(expr)` (with `Date` visual context) → `CALCULATE(expr, FILTER(ALLSELECTED(Table[Date]), Table[Date] <= MAX(Table[Date])))`
  * `RANK(expr)` → `RANKX(ALLSELECTED(Table[Dim]), expr, , DESC)`

### 5.4. Multi-Level Validation & Error Detection
* **Structural Comparison:** Normalizes whitespace and table qualifiers to verify AST parity.
* **Error Diagnosis:** Automatically classifies legacy conversion defects into:
  1. `inverted_aggregation_and_unsafe_division`
  2. `incorrect_lod_conversion`
  3. `expression_truncation`
  4. `return_type_mismatch`
  5. `semantic_mismatch` (general fallback)
* **Numerical Simulation:** Computes expected Tableau vs. DAX values in memory on `sample_data.csv` using Pandas. Detects discrepancies where error exceeds ε = 10⁻⁵.

### 5.5. Multi-Factor Confidence Scoring Formula

```
C = 0.20 × S_syntax + 0.35 × S_semantic + 0.25 × S_validation + 0.20 × S_context
```

* **Syntax (0.20):** Did the formula parse without errors?
* **Semantic (0.35):** Were all functions recognized? Was LOD present? Table calcs?
* **Validation (0.25):** Did numerical simulation match expected values?
* **Context (0.20):** For table calcs, was visual shelf context available?

**Hard Overrides:**
* Circular dependencies → C = 0.0
* Syntax errors → C = 0.0
* Proven numerical contradictions → C ≤ 0.30

---

## 6. Before-vs-After Accuracy Benchmark Results

The benchmark is evidence-based. Structural metrics compare the actual legacy/generated DAX against the supplied ground truth after harmless formatting and table-qualification normalization. Numerical metrics use the numerical validation engine. No benchmark percentage is hard-coded.

One ground-truth target (`calc_3`) contains an explicit `...` placeholder, so it cannot be fully certified. It is excluded from structural and numerical certification denominators and is not counted as a fully verified correction.

| Metric Category | Baseline ("Before") | Engine ("After") | Improvement / Result |
| :--- | :---: | :---: | :---: |
| **DAX Structural Accuracy** | **0.0% (0/3)** | **100.0% (3/3)** | **+100.0%** |
| **Numerical Agreement Rate** | **0.0% (0/3)** | **100.0% (3/3)** | **+100.0%** |
| **Visual Mapping Accuracy** | N/A | **100.0% (2/2)** | **100.0%** |
| **Flaw Detection Sensitivity** | N/A | **100.0% (4/4)** | **All labelled flaws detected** |
| **Correction Success Rate** | N/A | **75.0% (3/4)** | **3 fully verified; 1 unverifiable** |
| **Mean Calibrated Confidence** | **0.30** | **0.94** | **+0.64** |

### Important interpretation

* `calc_1`, `calc_2`, and `calc_4` are fully verifiable and pass both structural and numerical validation after correction.
* `calc_3` is detected as flawed and a best-effort DAX translation is produced, but its supplied ground truth is incomplete (`...`). Therefore it is **not** counted as a fully verified correction.
* This is intentionally more conservative than reporting a misleading 100% correction rate.

### Detailed Item Comparison

1. **`calc_1` (`Profit_Ratio`)**
   * Before: `SUM(Sales) / SUM(Profit)`
   * After: `DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))`
   * Structural: PASS
   * Numerical: PASS

2. **`calc_2` (`Region_Sales`)**
   * Before: `SUM(Sales)`
   * After: `CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region]))`
   * Structural: PASS
   * Numerical: PASS

3. **`calc_3` (`Advanced_KPI`)**
   * Before: `AVG(Profit)`
   * After: generated compound conditional preserving the FIXED region condition and WINDOW_SUM intent
   * Structural: NOT CERTIFIABLE because the supplied target contains `...`
   * Numerical: true branch verified; complete calculation remains unverifiable

4. **`calc_4` (`Sales_Category`)**
   * Before: `IF(SUM(Sales) > 5000, 1, 0)`
   * After: `IF(SUM(Table[Sales]) > 5000, "High", "Low")`
   * Structural: PASS
   * Numerical/type validation: PASS

## 7. Error Analysis

Each detected error is categorized, explained, and corrected:

| Error Category | Count | Example Calc | Cause | Solution Applied |
| :--- | :---: | :--- | :--- | :--- |
| `inverted_aggregation_and_unsafe_division` | 1 | calc_1 | Numerator/denominator swapped; raw `/` used | Used `DIVIDE()` with correct field order |
| `incorrect_lod_conversion` | 1 | calc_2 | FIXED LOD completely stripped | Emitted `CALCULATE(..., ALLEXCEPT(...))` |
| `expression_truncation` | 1 | calc_3 | Compound IF/LOD/WINDOW_SUM reduced to scalar | Full conditional tree preserved in IR |
| `return_type_mismatch` | 1 | calc_4 | String labels coerced to integers | Preserved string literal return type |

### Limitations per Error Category:
* **LOD Conversion:** INCLUDE and EXCLUDE LOD types are supported but not exercised in the test data.
* **Table Calculations:** Without full Tableau workbook `.twb` shelf metadata, partition/sort axes must be inferred from `visuals.json`. When no visual context is available (e.g., `RankSales`), the engine emits a parameterized template and lowers confidence to 0.73.
* **calc_3 Ground Truth:** Contains `...` (ellipsis) in the ELSE branch — the full correct ELSE DAX is not specified. The engine produces `CALCULATE(SUM(Table[Profit]), ALLSELECTED(Table))` as a best-effort candidate and marks status as `UNVERIFIABLE_INCOMPLETE_TEMPLATE`.

---

## 8. Machine Learning Decision

**Dataset size:** 4 core calculations + 3 dependencies + 2 XML calcs = **9 total formulas**.

This is **far too small for supervised machine learning**. Any ML model trained on 9 samples would severely overfit and produce unreliable predictions. The deterministic compiler-based approach is the only mathematically sound strategy for this dataset size.

**If scaled to enterprise volumes (10,000+ workbooks)**, potential ML applications would include:
* Candidate DAX ranking (selecting the best translation from multiple candidates)
* Confidence prediction calibration
* Organization-specific visual theme classification
* Error pattern classification from historical migration logs

---

## 9. How to Run & Verify

### Installation:
```bash
pip install -r requirements.txt
```

### Execute End-to-End Pipeline:
```bash
python main.py
```
This generates 5 output files in `output/`:
* `migration_results.json` — Primary output per company schema
* `benchmark_report.md` — Markdown before-vs-after summary
* `error_analysis.json` — Detailed error analysis with numerical evidence
* `dependency_chain_results.json` — Multi-step dependency DAX translations
* `xml_table_calc_results.json` — XML table calculation DAX translations

### Run Comprehensive Test Suite:
```bash
python run_all_tests.py
```
Or run individual suites:
```bash
python tests/test_ingestion.py
python tests/test_resolver.py
python tests/test_parser_and_ir.py
python tests/test_emitter.py
python tests/test_validation.py
python tests/test_visual_and_scorer.py
python tests/test_end_to_end.py
```
**Test Suite Status:** 88/88 tests passing (100% pass rate), including dedicated evaluation-metric tests.

---

## 10. Sample Primary Output (`output/migration_results.json`)

```json
[
  {
    "predicted_dax": "DIVIDE(SUM(Table[Profit]), SUM(Table[Sales]))",
    "visual_mapping": "clustered column chart",
    "confidence_score": 1.0,
    "is_corrected": true
  },
  {
    "predicted_dax": "CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region]))",
    "visual_mapping": "table",
    "confidence_score": 0.98,
    "is_corrected": true
  },
  {
    "predicted_dax": "IF(CALCULATE(SUM(Table[Sales]), ALLEXCEPT(Table, Table[Region])) > 10000, DIVIDE(AVG(Table[Profit]), SUM(Table[Sales])), CALCULATE(SUM(Table[Profit]), ALLSELECTED(Table)))",
    "visual_mapping": "table",
    "confidence_score": 0.77,
    "is_corrected": true
  },
  {
    "predicted_dax": "IF(SUM(Table[Sales]) > 5000, \"High\", \"Low\")",
    "visual_mapping": "table",
    "confidence_score": 1.0,
    "is_corrected": true
  }
]
```

---

## 11. Limitations & Future Improvements

1. **Table Calculations without Visual Shelf Metadata:** Table calculations in isolation (such as `RankSales`) lack partition and sort axes. The engine currently emits parameterized templates and penalizes confidence. Future work can integrate report workbook XML layout files (`.twb` XML shelves) to automatically parse the visual shelf configuration for every calculation.
2. **Machine Learning Integration:** While rule-based compilation is mathematically necessary for small datasets (N < 15), in large-scale enterprise deployments (N > 10,000 workbooks), a hybrid machine-learning candidate ranker could be trained to predict organization-specific visual themes and naming conventions.
3. **Numerical Validation Scope:** The numerical engine currently validates against the provided `sample_data.csv`. Calculations that require Tableau visual/table-calculation execution context (e.g., RUNNING_SUM ordering) cannot be fully numerically validated without the actual BI tool runtime.
4. **INCLUDE/EXCLUDE LOD:** While the parser and emitter support INCLUDE and EXCLUDE LOD types, these are not exercised in the test data and therefore untested empirically.
5. **ELSEIF Chaining:** The parser supports ELSEIF but no test calculation exercises deeply nested ELSEIF chains.
