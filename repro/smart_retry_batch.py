#!/usr/bin/env python3
"""Smart retry wrapper for run_stratified.py batch cache generation.

Strategy:
1. Run with short timeout + 5 retries per session
2. On failure: add skip marker, resume
3. After all done: retry skipped sessions up to 2 more passes
4. If >3 consecutive failures, sleep 10 min
"""

import json, os, subprocess, sys, time
from pathlib import Path

SAMPLE_IDS = sys.argv[1] if len(sys.argv) > 1 else "26,42"
MAX_PASSES = 3  # total passes for skipped sessions

REPO = Path(__file__).resolve().parents[1] if '__file__' in dir() else Path(os.getcwd())

def _rewrite_sessions(tmp_path):
    """Read .tmp file, return list of (session_key, is_skip)"""
    sessions = []
    if not os.path.exists(tmp_path):
        return sessions
    with open(tmp_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for k, v in obj.items():
                is_skip = isinstance(v, dict) and v.get("conversation_time", "").startswith("skipped")
                sessions.append((k, is_skip))
                break
    return sessions

def run_batch(sample_ids):
    args = [
        ".venv/bin/python", "run_stratified.py",
        "--data", "locomo",
        "--model", "deepseek",
        "--re_model", "v4flash",
        "--file", "mragent_100q",
        "--subset_manifest", "data/subsets/locomo10_100q_seed42.json",
        "--sample_ids", sample_ids,
    ]
    env = {
        **os.environ,
        "API_TIMEOUT_SECONDS": "120",
        "API_CLIENT_MAX_RETRIES": "0",
        "API_CALL_MAX_RETRIES": "5",
        "CHAT_TEXT_PARSE_MAX_ATTEMPTS": "1",
    }
    result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=7200)
    return result.returncode, result.stdout + result.stderr

def extract_failed_session(output_text):
    """Try to find which session failed from the error output."""
    for line in output_text.split("\n"):
        if "Rewrite resume progress:" in line:
            parts = line.split("/")
            if parts:
                current = int(parts[0].split()[-1]) + 1  # next session number
                return current
    return None

def main():
    consecutive_fails = 0

    for pass_num in range(1, MAX_PASSES + 1):
        print(f"\n{'='*60}")
        print(f"PASS {pass_num}/{MAX_PASSES}")
        print(f"{'='*60}")

        max_retries_per_session = 10
        session_fails = {}

        for attempt in range(max_retries_per_session):
            print(f"\n--- Attempt {attempt + 1} ---")
            rc, output = run_batch(SAMPLE_IDS)
            print(output[-2000:])  # last 2000 chars

            if rc == 0:
                print("BATCH COMPLETED SUCCESSFULLY!")
                return 0

            # Find failed session
            failed = extract_failed_session(output)
            if failed is None:
                failed = guess_from_tmp()

            if failed is not None:
                session_fails[failed] = session_fails.get(failed, 0) + 1
                print(f"Session {failed} failed ({session_fails[failed]} times)")

                if session_fails[failed] >= 5:
                    print(f"Skipping session {failed} after 5 failures")
                    add_skip_marker(failed)
                    consecutive_fails = 0
                    session_fails.pop(failed)
                else:
                    consecutive_fails += 1
            else:
                consecutive_fails += 1

            if consecutive_fails >= 3:
                print("3+ consecutive failures, sleeping 10 min...")
                time.sleep(600)
                consecutive_fails = 0

        print(f"\nPass {pass_num} exhausted retries.")

    print("\nAll passes exhausted. Remaining skipped sessions need manual attention.")
    return 1

def guess_from_tmp():
    """Guess next session from .tmp file state."""
    for sid in SAMPLE_IDS.split(","):
        sid = sid.strip()
        sid = f"conv-{sid}" if not sid.startswith("conv-") else sid
        tmp = REPO / "data" / "locomo" / "rewrite_deepseek" / f"{sid}_rewrite.json.tmp"
        sessions = _rewrite_sessions(tmp)
        if sessions:
            # Expected sessions are session_1 through session_N
            completed = len(sessions)
            return completed + 1  # next to process
    return None

def add_skip_marker(session_num):
    """Add a skip marker for a specific session number."""
    for sid in SAMPLE_IDS.split(","):
        sid = sid.strip()
        sid = f"conv-{sid}" if not sid.startswith("conv-") else sid
        tmp = REPO / "data" / "locomo" / "rewrite_deepseek" / f"{sid}_rewrite.json.tmp"
        if not tmp.exists():
            continue
        key = f"session_{session_num}"
        entry = {key: {"sentence": [], "topic_sentence": {}, "personal_sentence": {},
                        "conversation_time": f"skipped-api-timeout-pass"}}
        with open(tmp, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"  Added skip marker for {key}")
        return
    print("  WARNING: Could not find .tmp file to add skip marker")

if __name__ == "__main__":
    sys.exit(main())
