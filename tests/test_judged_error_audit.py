from repro.audit_mragent_judged_errors import automatic_cause, evidence_status


def test_evidence_hit_normalizes_sentence_ids():
    row = {"evidence": ["D1:4"], "prediction_context": ["D1:4-2", "D3:1"]}
    assert evidence_status(row) == (True, 1, 2)


def test_execution_error_has_priority():
    cause, tags, manual = automatic_cause(
        {"prediction": "ERROR", "_metrics": {}}, 1, False, 1, True, {})
    assert cause == "execution_or_schema_failure"
    assert tags == []
    assert manual is False


def test_human_semantic_acceptance_marks_judge_false_negative():
    cause, _, manual = automatic_cause(
        {"prediction": "semantically correct", "_metrics": {}},
        4,
        True,
        1,
        True,
        {"semantic_correct": "true"},
    )
    assert cause == "judge_false_negative"
    assert manual is False


def test_retrieval_miss_remains_manual_reviewable():
    cause, tags, manual = automatic_cause(
        {"prediction": "wrong", "_metrics": {"tool_calls": 4}}, 1, False, 2, True, {})
    assert cause == "tool_selection_or_path_failure"
    assert tags == []
    assert manual is True

