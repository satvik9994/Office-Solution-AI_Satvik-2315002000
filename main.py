"""Automated BI Migration Accuracy Engine - Main Pipeline Orchestrator."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import sys
import json
sys.path.insert(0, os.path.abspath("src"))

from src.ingestion.file_reader import (
    load_calculations,
    load_dependencies,
    load_tableau_xml,
    load_incorrect_dax,
    load_ground_truth,
    load_visuals,
    load_sample_data,
)
from src.resolver.dependency_graph import DependencyResolver
from src.parser.parser import Parser
from src.translator.dax_emitter import DAXEmitter
from src.validation.error_detector import ErrorDetector
from src.validation.numerical_engine import NumericalEngine
from src.visual_mapping.visual_mapper import VisualMapper
from src.intelligence.scorer import ConfidenceScorer
from src.evaluation.metrics import MetricsCalculator
from src.evaluation.reporter import OutputReporter
from src.ir.ir_nodes import IRTableCalculation


def run_pipeline():
    print("=" * 80)
    print("      AUTOMATED BI MIGRATION ACCURACY ENGINE - EXECUTION PIPELINE")
    print("=" * 80)

    # 1. Ingestion
    print("\n[1/8] Ingesting and Sanitizing Uploaded Tableau & DAX Artifacts...")
    calcs = load_calculations("data/tableau_calculations.json")
    deps = load_dependencies("data/tableau_dependencies.json")
    xml_calcs = load_tableau_xml("data/tableau_xml.xml")
    incorrect_map = load_incorrect_dax("data/incorrect_dax.json")
    ground_truth_map = load_ground_truth("data/ground_truth.json")
    visuals = load_visuals("data/visuals.json")
    df = load_sample_data("data/sample_data.csv")
    print(f"  -> Ingested {len(calcs)} core calculations, {len(deps)} dependent steps, {len(xml_calcs)} XML items.")
    print(f"  -> Ingested {len(incorrect_map)} baseline flawed DAX items and {len(ground_truth_map)} ground truth targets.")
    print(f"  -> Loaded sample data ({df.shape[0]} rows, {df.shape[1]} columns).")

    # 2. Dependency Resolution
    print("\n[2/8] Building Dependency DAG & Topologically Ordering Calculations...")
    physical_cols = set(df.columns)
    resolver = DependencyResolver(physical_cols)
    sorted_deps = resolver.resolve_items(deps)
    print("  -> Resolved execution order for dependent pipeline:")
    for idx, dep in enumerate(sorted_deps, 1):
        print(f"     Step {idx}: {dep.name} = {dep.formula}")

    # 3. Visual Mapping & Context Extraction
    print("\n[3/8] Mapping Visuals & Extracting Context for Table Calculations...")
    visual_mapper = VisualMapper()
    visual_results = []
    calc_to_visual_map = {}
    for vis in visuals:
        v_res = visual_mapper.map_visual(
            visual_id=vis.id,
            tableau_visual=vis.tableau_visual,
            dimensions=vis.dimensions,
            measures=vis.measures,
            expected_powerbi=vis.expected_powerbi,
        )
        visual_results.append(v_res)
        for m in vis.measures:
            calc_to_visual_map[m] = v_res.predicted_powerbi
        print(f"  -> {vis.id}: Tableau {vis.tableau_visual} -> Power BI {v_res.predicted_powerbi} (Conf: {v_res.confidence})")

    visual_context = visual_mapper.extract_visual_context_for_measures(visuals)

    # 4. Translation, Validation, and Correction for Core Calculations
    print("\n[4/8] Parsing AST, Generating DAX, and Executing Multi-Level Validation...")
    emitter = DAXEmitter(table_name="Table", physical_columns=physical_cols)
    detector = ErrorDetector()
    num_engine = NumericalEngine(df)
    scorer = ConfidenceScorer()

    processed_items = []
    evaluation_records = []
    error_analysis = []

    for c in calcs:
        ir = Parser.parse_formula(c.formula)

        # Context injection for Table Calculations if available
        if c.name in visual_context:
            order_dims = visual_context[c.name].get("order_by", [])
            if isinstance(ir, IRTableCalculation) and order_dims:
                # IR nodes are frozen, so rebuild with context injected
                ir = IRTableCalculation(
                    calc_type=ir.calc_type,
                    inner_expression=ir.inner_expression,
                    partition_by=list(ir.partition_by),
                    order_by=list(ir.order_by) + order_dims,
                )

        predicted_dax = emitter.emit(ir)
        legacy_dax = incorrect_map[c.id].dax if c.id in incorrect_map else ""
        target_dax = ground_truth_map[c.id].dax if c.id in ground_truth_map else ""

        # Error detection
        detection = detector.diagnose_and_correct(
            calc_id=c.id,
            tableau_formula=c.formula,
            legacy_dax=legacy_dax,
            generated_dax=predicted_dax,
            ground_truth_dax=target_dax,
        )

        # Numerical validation
        num_res_legacy = num_engine.validate_calc(c.id, c.formula, legacy_dax, is_legacy=True)
        num_res_corrected = num_engine.validate_calc(c.id, c.formula, predicted_dax, is_legacy=False)

        # Evidence-based structural comparison against the supplied ground truth.
        # calc_3 is intentionally marked unverifiable because its target contains "...".
        ground_truth_verifiable = bool(target_dax) and "..." not in target_dax
        baseline_structural_match = (
            MetricsCalculator.structural_match(legacy_dax, target_dax)
            if ground_truth_verifiable else False
        )
        engine_structural_match = (
            MetricsCalculator.structural_match(predicted_dax, target_dax)
            if ground_truth_verifiable else False
        )

        # The supplied incorrect_dax.json is the benchmark-labelled baseline set.
        is_flawed = c.id in incorrect_map
        flaw_detected = detection.is_incorrect

        baseline_numerical_status = num_res_legacy.status
        engine_numerical_status = num_res_corrected.status
        baseline_numerical_match = (
            num_res_legacy.is_match
            if baseline_numerical_status in ("VERIFIED", "MISMATCH") else False
        )
        engine_numerical_match = (
            num_res_corrected.is_match
            if engine_numerical_status in ("VERIFIED", "MISMATCH") else False
        )

        # Full correction certification requires structural parity and, when
        # numerical validation is available, numerical parity as well.
        correction_fully_verified = (
            is_flawed
            and ground_truth_verifiable
            and engine_structural_match
            and engine_numerical_status == "VERIFIED"
            and engine_numerical_match
        )

        # Confidence calculation
        has_lod = "fixed" in c.formula.lower()
        has_table_calc = any(tc in c.formula.lower() for tc in ["window_sum", "running_sum", "rank"])
        has_vis_ctx = c.name in visual_context
        is_ellipsis = "..." in target_dax

        conf_breakdown = scorer.calculate(
            has_lod=has_lod,
            has_table_calc=has_table_calc,
            has_visual_context=has_vis_ctx,
            numerical_match=num_res_corrected.is_match,
            is_template_ellipsis=is_ellipsis,
        )

        visual_mapping_str = calc_to_visual_map.get(c.name, "table")

        item_dict = {
            "id": c.id,
            "name": c.name,
            "predicted_dax": predicted_dax,
            "visual_mapping": visual_mapping_str,
            "confidence_score": conf_breakdown.overall_score,
            "is_corrected": correction_fully_verified,
            "legacy_dax": legacy_dax,
            "ground_truth_dax": target_dax,
            "error_category": detection.error_category,
            "is_flawed_baseline": is_flawed,
            "flaw_detected": flaw_detected,
            "ground_truth_verifiable": ground_truth_verifiable,
            "baseline_structural_match": baseline_structural_match,
            "engine_structural_match": engine_structural_match,
            "baseline_numerical_match": baseline_numerical_match,
            "engine_numerical_match": engine_numerical_match,
            "baseline_numerical_status": baseline_numerical_status,
            "engine_numerical_status": engine_numerical_status,
            "correction_fully_verified": correction_fully_verified,
            # Keep confidence transparent: the legacy baseline starts at the
            # calibrated default used by the scorer rather than a fake accuracy.
            "baseline_confidence": 0.30 if is_flawed else 0.90,
            "engine_confidence": conf_breakdown.overall_score,
        }
        processed_items.append(item_dict)
        evaluation_records.append(item_dict)

        # Build error analysis entry
        if detection.is_incorrect:
            error_analysis.append({
                "id": c.id,
                "name": c.name,
                "error_category": detection.error_category,
                "explanation": detection.explanation,
                "legacy_dax": legacy_dax,
                "corrected_dax": predicted_dax,
                "ground_truth_dax": target_dax,
                "numerical_legacy": {"value": num_res_legacy.dax_value, "status": num_res_legacy.status},
                "numerical_corrected": {"value": num_res_corrected.dax_value, "status": num_res_corrected.status},
                "confidence": conf_breakdown.overall_score,
            })

    # 5. Translate Dependency Chain Calculations
    print("\n[5/8] Translating Multi-Step Dependency Chain to DAX...")
    dep_results = []
    for dep in sorted_deps:
        ir = Parser.parse_formula(dep.formula)
        dep_dax = emitter.emit(ir)
        dep_results.append({"name": dep.name, "formula": dep.formula, "dax": dep_dax})
        print(f"  -> {dep.name}: {dep.formula} => {dep_dax}")

    # 6. Translate XML Table Calculations
    print("\n[6/8] Translating XML-Embedded Table Calculations to DAX...")
    xml_results = []
    for xc in xml_calcs:
        ir = Parser.parse_formula(xc.formula)
        # Inject visual context if available
        if xc.name in visual_context:
            order_dims = visual_context[xc.name].get("order_by", [])
            if hasattr(ir, "order_by") and order_dims:
                # Since IR nodes are frozen, we rebuild with context
                if isinstance(ir, IRTableCalculation):
                    ir = IRTableCalculation(
                        calc_type=ir.calc_type,
                        inner_expression=ir.inner_expression,
                        partition_by=list(ir.partition_by),
                        order_by=list(ir.order_by) + order_dims,
                    )
        xc_dax = emitter.emit(ir)

        has_tc = any(tc in xc.formula.lower() for tc in ["window_sum", "running_sum", "rank"])
        has_ctx = xc.name in visual_context
        xc_conf = scorer.calculate(has_table_calc=has_tc, has_visual_context=has_ctx, numerical_match=None)

        xml_results.append({
            "name": xc.name, "formula": xc.formula, "dax": xc_dax,
            "confidence": xc_conf.overall_score, "has_visual_context": has_ctx,
        })
        ctx_note = " (with visual context)" if has_ctx else " (no visual context - lower confidence)"
        print(f"  -> {xc.name}: {xc.formula} => {xc_dax} (Conf: {xc_conf.overall_score}){ctx_note}")

    # 7. Metrics & Reporting
    print("\n[7/8] Calculating Before-vs-After Metrics and Benchmarks...")
    summary = MetricsCalculator.calculate_summary(evaluation_records, visual_results)

    print("\n" + "=" * 80)
    print("                     BEFORE VS AFTER ACCURACY BENCHMARK")
    print("=" * 80)
    print(f"  DAX Structural Accuracy:      Baseline: {summary.baseline_dax_accuracy}%  -->  Engine: {summary.engine_dax_accuracy}%  (Gain: +{summary.net_accuracy_gain}%)")
    print(f"  Numerical Agreement Rate:     Baseline: {summary.baseline_numerical_agreement_rate}%  -->  Engine: {summary.numerical_agreement_rate}%")
    print(f"  Flaw Detection Sensitivity:   {summary.flaw_detection_rate}% ({summary.detection_numerator}/{summary.detection_denominator})")
    print(f"  Correction Success Rate:      {summary.correction_success_rate}% ({summary.correction_numerator}/{summary.correction_denominator})")
    print(f"  Visual Mapping Accuracy:      {summary.visual_mapping_accuracy}%")
    print(f"  Mean Confidence Score:        Baseline: {summary.baseline_mean_confidence}  -->  Engine: {summary.engine_mean_confidence}")
    print("=" * 80)

    # 8. Export Outputs
    print("\n[8/8] Generating Deliverable Artifacts...")
    company_payload = OutputReporter.generate_json_payload(processed_items)
    
    os.makedirs("output", exist_ok=True)
    with open("output/migration_results.json", "w") as f:
        json.dump(company_payload, f, indent=2)
    print("  -> Exported primary JSON contract: output/migration_results.json")

    markdown_report = OutputReporter.generate_markdown_report(summary, evaluation_records, visual_results)
    with open("output/benchmark_report.md", "w") as f:
        f.write(markdown_report)
    print("  -> Exported detailed Markdown report: output/benchmark_report.md")

    # Export error analysis
    with open("output/error_analysis.json", "w") as f:
        json.dump(error_analysis, f, indent=2, default=str)
    print("  -> Exported error analysis: output/error_analysis.json")

    # Export dependency chain results
    with open("output/dependency_chain_results.json", "w") as f:
        json.dump(dep_results, f, indent=2)
    print("  -> Exported dependency chain translations: output/dependency_chain_results.json")

    # Export XML table calculation results
    with open("output/xml_table_calc_results.json", "w") as f:
        json.dump(xml_results, f, indent=2)
    print("  -> Exported XML table calculation translations: output/xml_table_calc_results.json")

    print("\nPIPELINE EXECUTION COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    run_pipeline()

