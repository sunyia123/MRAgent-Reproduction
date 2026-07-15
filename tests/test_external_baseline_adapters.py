import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repro.external_baselines.adapter_common import conversation_units, question_items
from repro.external_baselines.run_mem0_adapter import LoggedCompletions, normalize_search_results


class ExternalBaselineAdapterTests(unittest.TestCase):
    def test_image_only_turn_is_preserved_with_date_and_role(self):
        conversation = {
            "speaker_a": "Alice",
            "speaker_b": "Bob",
            "session_1_date_time": "1 January 2024",
            "session_1": [
                {
                    "dia_id": "D1:1",
                    "speaker": "Alice",
                    "text": "",
                    "blip_caption": "a red bicycle",
                }
            ],
        }
        units = conversation_units(conversation)
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["origin"], "D1:1")
        self.assertEqual(units[0]["session_date"], "1 January 2024")
        self.assertEqual(units[0]["role"], "user")
        self.assertIn("a red bicycle", units[0]["text"])

    def test_question_items_keep_exact_manifest_indices(self):
        questions = [
            {"question": "q0", "category": 1},
            {"question": "q1", "category": 2},
            {"question": "q2", "category": 4},
        ]
        items = question_items("conv-1", questions, [0, 2])
        self.assertEqual([item[0] for item in items], [0, 2])

    def test_mem0_results_expose_source_ids(self):
        rows = normalize_search_results(
            {
                "results": [
                    {
                        "id": "m1",
                        "memory": "[source=D2:4] Alice bought a camera.",
                        "score": 0.8,
                        "metadata": {"source_id": "D2:4", "session_date": "2 Jan 2024"},
                    }
                ]
            }
        )
        self.assertEqual(rows[0]["source_ids"], ["D2:4"])
        self.assertEqual(rows[0]["source_id"], "D2:4")

    def test_mem0_internal_calls_force_thinking_off_and_log_payload(self):
        class Response:
            def model_dump(self, mode=None):
                return {"choices": [{"message": {"content": "ok"}}]}

        class Target:
            def __init__(self):
                self.kwargs = None

            def create(self, **kwargs):
                self.kwargs = kwargs
                return Response()

        with TemporaryDirectory() as directory:
            target = Target()
            log_path = Path(directory) / "calls.jsonl"
            response = LoggedCompletions(target, log_path).create(
                model="deepseek-ai/DeepSeek-V4-Flash",
                messages=[{"role": "user", "content": "test"}],
            )
            self.assertIsInstance(response, Response)
            self.assertEqual(target.kwargs["extra_body"], {"enable_thinking": False})
            records = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 2)
            self.assertIn('"status": "started"', records[0])
            self.assertIn('"status": "success"', records[1])


if __name__ == "__main__":
    unittest.main()
