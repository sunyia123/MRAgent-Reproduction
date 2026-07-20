import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import eval.judge as judge
from eval.judge import build_judge_prompt, judge_done_sets, order_rows_by_manifest, parse_judge_label


def _assert_value_error(raw):
    try:
        parse_judge_label(raw)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_judge_done_sets_support_old_and_new_rows():
    by_index, by_question = judge_done_sets([
        {"sample": "conv-26", "question": "old row"},
        {"sample": "conv-30", "question": "new row", "question_index": 8},
    ])
    assert by_index == {("conv-30", 8)}
    assert by_question == {("conv-26", "old row"), ("conv-30", "new row")}


def test_parse_judge_label_is_strict_and_case_insensitive():
    assert parse_judge_label('{"label":"correct"}') == "CORRECT"
    assert parse_judge_label('{"label":"WRONG"}') == "WRONG"
    _assert_value_error('{"label":"MAYBE"}')
    _assert_value_error('[{"label":"CORRECT"}]')


def test_judge_prompt_renders_literal_json_examples():
    prompt = build_judge_prompt("Q?", "gold", "prediction")
    assert '{"label":"CORRECT"}' in prompt
    assert "Question: Q?" in prompt


def test_judge_manifest_controls_question_order():
    with tempfile.TemporaryDirectory() as directory:
        manifest = Path(directory) / "manifest.json"
        manifest.write_text(json.dumps({"records": [
            {"sample_id": "conv-30", "question_index": 2},
            {"sample_id": "conv-26", "question_index": 1},
        ]}), encoding="utf-8")
        rows = [
            {"sample": "conv-26", "question_index": 1},
            {"sample": "conv-30", "question_index": 2},
        ]
        ordered = order_rows_by_manifest(rows, manifest)
    assert [(row["sample"], row["question_index"]) for row in ordered] == [
        ("conv-30", 2), ("conv-26", 1)
    ]


def test_judge_records_parse_retry_before_success():
    responses = iter(['not json', '{"label":"CORRECT"}'])

    def create(**_kwargs):
        content = next(responses)
        return SimpleNamespace(
            id="response-id",
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=content, reasoning_content=None),
            )],
            usage=SimpleNamespace(
                prompt_tokens=10, completion_tokens=2, total_tokens=12,
            ),
        )

    old_client = judge._client
    old_attempts = judge.JUDGE_CALL_MAX_ATTEMPTS
    judge._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    judge.JUDGE_CALL_MAX_ATTEMPTS = 2
    try:
        result = judge.evaluate_llm_judge_detailed("Q", "A", "A")
    finally:
        judge._client = old_client
        judge.JUDGE_CALL_MAX_ATTEMPTS = old_attempts

    assert result["llm_score"] == 1
    assert result["judge_retries"] == 1
    assert [item["status"] for item in result["judge_attempts"]] == [
        "parse_error", "response"
    ]
