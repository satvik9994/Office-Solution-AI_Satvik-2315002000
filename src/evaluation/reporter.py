"""Generates company output and evidence-based benchmark reports."""

from typing import Dict, List, Any
from evaluation.metrics import BenchmarkSummary


class OutputReporter:
    """Formats and exports migration outputs and benchmark reports."""

    @staticmethod
    def format_company_output(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "predicted_dax": item["predicted_dax"],
            "visual_mapping": item["visual_mapping"],
            "confidence_score": item["confidence_score"],
            "is_corrected": item["is_corrected"],
        }

    @staticmethod
    def generate_json_payload(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [OutputReporter.format_company_output(it) for it in items]

    @staticmethod
    def generate_markdown_report(
        summary: BenchmarkSummary,
        detailed_items: List[Dict[str, Any]],
        visual_results: List[Any],
    ) -> str:
        lines = [
            "# Automated BI Migration Accuracy Engine - Benchmark Report",
            "",
            "## 1. Executive Summary Table",
            "",
            "| Metric Category | Baseline (Before) | Engine (After) | Improvement | Evidence |",
            "| :--- | ---: | ---: | ---: | :--- |",
            f"| **DAX Structural Accuracy** | **{summary.baseline_dax_accuracy}%** | **{summary.engine_dax_accuracy}%** | **+{summary.net_accuracy_gain}%** | {summary.structural_baseline_numerator}/{summary.structural_denominator} -> {summary.structural_engine_numerator}/{summary.structural_denominator} verifiable formulas |",
            f"| **Numerical Agreement Rate** | **{summary.baseline_numerical_agreement_rate}%** | **{summary.numerical_agreement_rate}%** | **+{round(summary.numerical_agreement_rate-summary.baseline_numerical_agreement_rate, 1)}%** | {summary.numerical_baseline_numerator}/{summary.numerical_denominator} baseline; {summary.numerical_engine_numerator}/{summary.numerical_denominator} engine |",
            f"| **Visual Mapping Accuracy** | N/A | **{summary.visual_mapping_accuracy}%** | **+{summary.visual_mapping_accuracy}%** | {sum(1 for v in visual_results if v.is_match)}/{len(visual_results)} matches |",
            f"| **Flaw Detection Sensitivity** | N/A | **{summary.flaw_detection_rate}%** | N/A | {summary.detection_numerator}/{summary.detection_denominator} labelled flaws detected |",
            f"| **Correction Success Rate** | N/A | **{summary.correction_success_rate}%** | N/A | {summary.correction_numerator}/{summary.correction_denominator} fully verified corrections |",
            f"| **Mean Calibrated Confidence** | {summary.baseline_mean_confidence} | **{summary.engine_mean_confidence}** | **+{round(summary.engine_mean_confidence-summary.baseline_mean_confidence, 2)}** | Mean over {len(detailed_items)} calculations |",
            "",
            "### Metric Integrity Note",
            "",
            f"- `{summary.incomplete_ground_truth_count}` ground-truth item(s) contain an incomplete template (`...`) and are excluded from structural/numerical certification metrics.",
            "- A correction is counted as successful only when the generated formula is structurally verified and its numerical validation is also verified where numerical validation is available.",
            "- No baseline metric is hard-coded; baseline values come from the supplied legacy DAX and numerical validation results.",
            "",
            "## 2. Before-vs-After Item Comparison",
            "",
            "| ID | Name | Baseline Structural | Engine Structural | Baseline Numerical | Engine Numerical | Correction Status | Confidence |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]

        for it in detailed_items:
            baseline_struct = "PASS" if it["baseline_structural_match"] else "FAIL"
            engine_struct = (
                "N/A"
                if not it["ground_truth_verifiable"]
                else ("PASS" if it["engine_structural_match"] else "FAIL")
            )
            baseline_num = it["baseline_numerical_status"]
            engine_num = it["engine_numerical_status"]
            if it["correction_fully_verified"]:
                correction = "VERIFIED"
            elif not it["ground_truth_verifiable"]:
                correction = "UNVERIFIABLE"
            else:
                correction = "FAILED"
            lines.append(
                f"| `{it['id']}` | {it['name']} | {baseline_struct} | {engine_struct} | "
                f"{baseline_num} | {engine_num} | {correction} | {it['confidence_score']} |"
            )

        lines.extend([
            "",
            "## 3. Visual Mapping Benchmark",
            "",
            "| Visual ID | Tableau Visual | Confidence | Predicted Power BI Visual | Target | Match? |",
            "| :--- | :--- | :---: | :--- | :--- | :---: |",
        ])

        for v in visual_results:
            lines.append(
                f"| `{v.visual_id}` | `{v.tableau_visual}` | {v.confidence} | "
                f"**`{v.predicted_powerbi}`** | `{v.expected_powerbi}` | "
                f"{'PASS' if v.is_match else 'FAIL'} |"
            )

        return "\n".join(lines) + "\n"
