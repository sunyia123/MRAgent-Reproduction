from agent.structured import normalize_question_keys, normalize_tag_scores


def test_question_keys_accept_singleton_object_list():
    value = [{
        "question_time": "",
        "keywords": [{"id": "Caroline", "alternatives": ["she"]}],
    }]
    assert normalize_question_keys(value) == {
        "question_time": "",
        "keywords": [{"id": "Caroline", "alternatives": ["she"]}],
    }


def test_question_keys_reject_raw_text_and_wrong_keyword_shape():
    assert normalize_question_keys("truncated json") is None
    assert normalize_question_keys({"question_time": "", "keywords": ["Caroline"]}) is None


def test_tag_scores_filter_unknown_and_invalid_scores():
    value = {
        "tag_scores": {
            "Travel": 1.2,
            "Family": 0.4,
            "Unknown": 0.9,
            "Broken": "high",
        }
    }
    assert normalize_tag_scores(value, ["Travel", "Family", "Broken"]) == {
        "Travel": 1.0,
        "Family": 0.4,
    }


def test_tag_scores_reject_wrong_root_type():
    assert normalize_tag_scores([], ["Travel"]) is None
    assert normalize_tag_scores({"tag_scores": []}, ["Travel"]) is None
