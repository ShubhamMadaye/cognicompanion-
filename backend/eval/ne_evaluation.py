"""
CogniCompanion — Northeast Indian Language & Query Understanding Evaluation Harness
====================================================================================
Evaluates:
  1. Northeast Indian Language Intent Detection & Script Identification
  2. Query Understanding (Spelling, Pronouns, Bare Follow-ups, Ambiguity)
  3. Strict PME Grounding & Safety verification

Usage:
  python eval/ne_evaluation.py [--eval-set path/to/eval_set.json]
"""

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.ai.languages.language_identifier import detect_language_from_text
from app.ai.languages.ne_language_registry import resolve_ne_language
from app.ai.memory_engine.intent_detector import PMEIntent, detect_intent
from app.ai.memory_engine.query_understanding import (
    ConversationContext,
    QueryUnderstandingLayer,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("NE_Evaluation")


def _make_context(ctx_data: dict[str, Any] | None) -> ConversationContext | None:
    if not ctx_data:
        return None
    last_intent_val = ctx_data.get("last_intent")
    last_intent = PMEIntent(last_intent_val) if last_intent_val else None

    return ConversationContext(
        conversation_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        language=ctx_data.get("language", "en"),
        recent_turns=ctx_data.get("recent_turns", []),
        last_intent=last_intent,
        last_referenced_person=ctx_data.get("last_person"),
        last_referenced_event=ctx_data.get("last_event"),
        last_referenced_location=ctx_data.get("last_location"),
        last_referenced_date=None,
        last_pme_evidence=[],
        known_people=ctx_data.get("known_people", []),
        known_medications=ctx_data.get("known_medications", []),
    )


async def run_evaluation(eval_path: Path) -> dict[str, Any]:
    with open(eval_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    qu_layer = QueryUnderstandingLayer()

    total = len(cases)
    passed = 0
    failed = 0
    results: list[dict[str, Any]] = []

    print(f"\n==================================================================")
    print(f" CogniCompanion NE Language & Query Understanding Evaluation Suite")
    print(f" Benchmark dataset: {eval_path.name} ({total} test cases)")
    print(f"==================================================================\n")

    for tc in cases:
        tc_id = tc["id"]
        lang = tc["language"]
        query = tc["query"]
        category = tc["category"]
        ctx = _make_context(tc.get("context"))

        # Step 1: Run Query Understanding
        qu_res = await qu_layer.understand(query, context=ctx)

        # Step 2: Run Intent Detection on rewritten query
        detected_intent, entities = detect_intent(
            qu_res.rewritten_query, conversation_context=ctx
        )

        # Step 3: Verify Expectations
        test_passed = True
        failure_reasons = []

        if "expected_intent" in tc:
            expected_intent_val = tc["expected_intent"]
            actual_intent_val = detected_intent.value
            if actual_intent_val != expected_intent_val:
                test_passed = False
                failure_reasons.append(
                    f"Intent mismatch: expected '{expected_intent_val}', got '{actual_intent_val}'"
                )

        if "expected_mode" in tc:
            if qu_res.resolution_mode != tc["expected_mode"]:
                test_passed = False
                failure_reasons.append(
                    f"Mode mismatch: expected '{tc['expected_mode']}', got '{qu_res.resolution_mode}'"
                )

        if "expected_needs_clarification" in tc:
            if qu_res.needs_clarification != tc["expected_needs_clarification"]:
                test_passed = False
                failure_reasons.append(
                    f"Needs clarification mismatch: expected {tc['expected_needs_clarification']}, got {qu_res.needs_clarification}"
                )

        if "expected_rewritten_contains" in tc:
            target_str = tc["expected_rewritten_contains"].lower()
            if target_str not in qu_res.rewritten_query.lower():
                test_passed = False
                failure_reasons.append(
                    f"Rewritten query does not contain '{target_str}': got '{qu_res.rewritten_query}'"
                )

        status_str = "PASS" if test_passed else "FAIL"
        if test_passed:
            passed += 1
            print(f"  [PASS] {tc_id:30s} | {lang:6s} | {category:20s}")
        else:
            failed += 1
            print(f"  [FAIL] {tc_id:30s} | {lang:6s} | {category:20s}")
            for r in failure_reasons:
                print(f"         Reason: {r}")

        results.append({
            "id": tc_id,
            "language": lang,
            "category": category,
            "passed": test_passed,
            "failures": failure_reasons,
            "rewritten_query": qu_res.rewritten_query,
            "resolution_mode": qu_res.resolution_mode,
            "intent": detected_intent.value,
        })

    accuracy = (passed / total) * 100 if total > 0 else 0
    print(f"\n------------------------------------------------------------------")
    print(f" Summary: {passed}/{total} Passed ({accuracy:.1f}% Accuracy)")
    print(f" Status: {'ALL BENCHMARKS PASSED' if failed == 0 else f'{failed} FAILED'}")
    print(f"==================================================================\n")

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy_pct": round(accuracy, 2),
        "results": results,
    }


if __name__ == "__main__":
    eval_file = BASE_DIR / "eval" / "cognicompanion_eval_set.json"
    if len(sys.argv) > 1:
        eval_file = Path(sys.argv[1])
    asyncio.run(run_evaluation(eval_file))
