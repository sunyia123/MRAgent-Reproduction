from collections import Counter

from repro.build_main_experiment_manifests import build_manifests
from repro.compare_main_experiment import clustered_delta_ci


def synthetic_data():
    rows = []
    for sample_number in range(10):
        qa = []
        for category, count in {1: 30, 2: 32, 3: 10, 4: 90, 5: 45}.items():
            for index in range(count):
                qa.append({
                    "question": f"sample {sample_number} category {category} question {index}",
                    "answer": "answer",
                    "evidence": [f"D1:{index + 1}"],
                    "category": category,
                })
        rows.append({"sample_id": f"conv-{sample_number}", "qa": qa})
    return rows


def test_build_manifests_has_exact_sizes_and_nested_ablation():
    data = synthetic_data()
    sample_ids = [row["sample_id"] for row in data]
    main, ablation = build_manifests(data, sample_ids, 42, "synthetic.json")

    assert main["n_questions"] == 500
    assert ablation["n_questions"] == 200
    assert main["category_counts"]["5"] == 100
    assert ablation["category_counts"] == {"1": 100, "2": 100}
    assert Counter(main["sample_counts"].values()) == {50: 10}

    main_keys = {(row["sample_id"], row["question_index"]) for row in main["records"]}
    ablation_keys = {(row["sample_id"], row["question_index"]) for row in ablation["records"]}
    assert ablation_keys <= main_keys


def test_build_manifests_is_deterministic():
    data = synthetic_data()
    sample_ids = [row["sample_id"] for row in data]
    first = build_manifests(data, sample_ids, 42, "synthetic.json")
    second = build_manifests(data, sample_ids, 42, "synthetic.json")
    assert first == second


def test_clustered_delta_ci_preserves_positive_paired_gap():
    full = {("conv-1", 0): 1.0, ("conv-1", 1): 0.8, ("conv-2", 0): 0.9}
    other = {("conv-1", 0): 0.5, ("conv-1", 1): 0.3, ("conv-2", 0): 0.4}
    delta, low, high, count = clustered_delta_ci(
        full, other, ["conv-1", "conv-2"], iterations=100)
    assert count == 3
    assert delta == 0.5
    assert low > 0
    assert high > 0
