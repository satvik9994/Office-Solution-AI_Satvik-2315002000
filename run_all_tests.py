"""Master Test Runner executing all 8 unit and integration test suites."""

import sys
import subprocess


def run_suite():
    suites = [
        "tests/test_ingestion.py",
        "tests/test_resolver.py",
        "tests/test_parser_and_ir.py",
        "tests/test_emitter.py",
        "tests/test_validation.py",
        "tests/test_visual_and_scorer.py",
        "tests/test_end_to_end.py",
        "tests/test_evaluation_metrics.py",
    ]

    total_passed = 0
    print("=" * 70)
    print("      AUTOMATED BI MIGRATION ENGINE - MASTER TEST SUITE")
    print("=" * 70)

    import re as _re
    for suite in suites:
        print(f"\nRunning {suite}...")
        res = subprocess.run([sys.executable, suite], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"FAILED: {suite}")
            print(res.stderr)
            sys.exit(1)
        else:
            lines = res.stderr.strip().splitlines()
            summary_line = [l for l in lines if "Ran" in l]
            info = summary_line[0] if summary_line else "OK"
            count_match = _re.search(r"Ran (\d+) test", info)
            if count_match:
                total_passed += int(count_match.group(1))
            print(f"  [PASS] {suite} ({info})")

    print("\n" + "=" * 70)
    print(f"ALL {len(suites)} TEST SUITES ({total_passed} TESTS) PASSED CLEANLY (100% PASS RATE)!")
    print("=" * 70)


if __name__ == "__main__":
    run_suite()
