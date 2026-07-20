from repro.validate_judge_results import row_key


def test_judge_row_key_requires_sample_and_question_index():
    assert row_key({"sample": "conv-26", "question_index": 4}) == ("conv-26", 4)
    assert row_key({"sample_id": "conv-30", "question_index": "8"}) == ("conv-30", 8)
    assert row_key({"sample": "conv-26"}) is None
