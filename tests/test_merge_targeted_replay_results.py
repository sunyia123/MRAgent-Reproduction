import json
import sys
import tempfile
from pathlib import Path

from repro.merge_targeted_replay_results import index_rows, is_execution_error, main, row_key


def test_repair_row_helpers_require_stable_keys():
    row = {"sample": "conv-26", "question_index": 4, "prediction": "answer"}
    assert row_key(row) == ("conv-26", 4)
    assert index_rows([row], "test") == {("conv-26", 4): row}
    assert not is_execution_error(row)
    assert is_execution_error({**row, "prediction": "ERROR"})


def test_merge_replaces_only_manifest_rows_and_keeps_full_count():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        result_root = root / "result"
        result_root.mkdir()
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "source_result_tag": "source",
            "records": [{"sample_id": "conv-26", "question_index": 1}],
        }), encoding="utf-8")
        source_rows = [
            {"sample": "conv-26", "question_index": 0, "prediction": "kept"},
            {"sample": "conv-26", "question_index": 1, "prediction": "ERROR"},
        ]
        replay_rows = [
            {"sample": "conv-26", "question_index": 1, "prediction": "fixed"},
        ]
        for tag, rows in (("source", source_rows), ("replay", replay_rows)):
            (result_root / f"conv-26_result_deepseek_{tag}.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

        old_argv = sys.argv
        sys.argv = [
            "merge_targeted_replay_results.py",
            "--manifest", str(manifest),
            "--replay_tag", "replay",
            "--output_tag", "repaired",
            "--result_root", str(result_root),
            "--report_prefix", str(root / "report"),
        ]
        try:
            main()
        finally:
            sys.argv = old_argv

        merged = [
            json.loads(line)
            for line in (result_root / "conv-26_result_deepseek_repaired.jsonl")
            .read_text(encoding="utf-8").splitlines()
        ]
        assert len(merged) == 2
        assert merged[0]["prediction"] == "kept"
        assert merged[1]["prediction"] == "fixed"
        assert merged[1]["_repair_provenance"]["source_tag"] == "source"
