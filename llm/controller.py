import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from openai import OpenAI, APIStatusError, APIConnectionError, APIResponseValidationError
from prompts.prompts import Prompts
from common.utils import extract_json_from_content
from common import config
from common.logging_utils import RUN_ID
import logging
logger = logging.getLogger(__name__)

# --- Per-call metadata logging (always-on; writes to result/diagnostics/) ---
_CALL_LOG_DIR = os.path.join("result", "diagnostics")
_CALL_LOG_PATH = os.path.join(_CALL_LOG_DIR, "api_call_log.jsonl")
_RUN_CALL_LOG_PATH = os.path.join(_CALL_LOG_DIR, f"api_call_log_{RUN_ID}.jsonl")
os.makedirs(_CALL_LOG_DIR, exist_ok=True)
_call_logger = logging.getLogger("llm.call_log")
_call_logger.setLevel(logging.INFO)
_call_logger.propagate = False
_call_fh = logging.FileHandler(_CALL_LOG_PATH, encoding="utf-8")
_call_fh.setFormatter(logging.Formatter('%(message)s'))
_call_logger.addHandler(_call_fh)
_run_call_fh = logging.FileHandler(_RUN_CALL_LOG_PATH, encoding="utf-8")
_run_call_fh.setFormatter(logging.Formatter('%(message)s'))
_call_logger.addHandler(_run_call_fh)


def _log_api_call(call_type: str, model: str, max_tokens: int, temperature: float,
                  finish_reason: str = None, usage: dict = None,
                  latency_s: float = 0.0, attempt: int = 1, error: str = None,
                  stage: str = None, session: str = None):
    """Always-on per-call metadata log for audit trail."""
    try:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_id": RUN_ID,
            "call_type": call_type,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "attempt": attempt,
            "latency_s": round(latency_s, 1),
        }
        if stage: rec["stage"] = stage
        if session: rec["session"] = session
        if finish_reason: rec["finish_reason"] = finish_reason
        if usage: rec["usage"] = usage
        if error: rec["error"] = str(error)[:500]
        _call_logger.info(json.dumps(rec, ensure_ascii=False, default=str))
    except Exception:
        pass  # call logging must never crash the pipeline

def _log_from_resp(call_type, req, resp, latency_s=0.0, attempt=1, stage=None, session=None):
    """Extract and log metadata from a successful API response."""
    try:
        choice = resp.choices[0]
        msg = getattr(choice, "message", None)
        usage = getattr(resp, "usage", None)
        _log_api_call(
            call_type=call_type,
            model=req.get("model", "?"),
            max_tokens=req.get("max_tokens", 0),
            temperature=req.get("temperature", 0.0),
            finish_reason=getattr(choice, "finish_reason", None),
            usage={"prompt": getattr(usage, "prompt_tokens", None),
                   "completion": getattr(usage, "completion_tokens", None),
                   "total": getattr(usage, "total_tokens", None)} if usage else None,
            latency_s=latency_s, attempt=attempt, stage=stage, session=session,
        )
    except Exception:
        pass


def _log_from_error(call_type, req, error, latency_s=0.0, attempt=1, stage=None, session=None):
    """Log a failed API call."""
    try:
        _log_api_call(
            call_type=call_type,
            model=req.get("model", "?"),
            max_tokens=req.get("max_tokens", 0),
            temperature=req.get("temperature", 0.0),
            latency_s=latency_s, attempt=attempt, error=error, stage=stage, session=session,
        )
    except Exception:
        pass


class LLM:
    def __init__(self):
        self.client = OpenAI(api_key=config.API_KEY,
                             base_url=config.LLM_BASE_URL,
                             timeout=config.API_TIMEOUT_SECONDS,
                             max_retries=config.API_CLIENT_MAX_RETRIES)
        self.model = config.MODEL
        # metrics instrumentation
        self.last_tool_calls = 0
        self._current_stage = None  # set by agent: "rewrite" / "keyword" / "qa"

    def chat_with_tool(
            self,
            *,
            messages: List[Dict[str, Any]],
            model: str = config.MODEL,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[Any] = "auto",
            use_tool: bool = True,
            temperature: float = 0.0,
            top_p: float = 1.0,
            seed: Optional[int] = 66,
            max_retries: Optional[int] = None,
            backoff: float = 1.5,
            **extra  # extra params, e.g. response_format
    ):
        """
        Robust wrapper around client.chat.completions.create:
        - catches 429/5xx/connection/validation errors with exponential backoff
        - supports passing tools / tool_choice
        - returns the OpenAI SDK ChatCompletion object
        """
        req = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            seed=seed,
        )
        if use_tool:
            req["tools"] = tools
            req["tool_choice"] = tool_choice
        if extra:
            req.update(extra)
        # Guard: prevent unbounded generation. Default from config (16384),
        # overridable per-call via extra or the caller.
        if "max_tokens" not in req:
            req["max_tokens"] = getattr(config, 'DEFAULT_MAX_TOKENS', 4096)
        if max_retries is None:
            max_retries = config.API_CALL_MAX_RETRIES

        last_exc: Optional[Exception] = None
        _t0 = 0.0
        for attempt in range(1, max_retries + 1):
            try:
                _t0 = time.time()
                resp =  self.client.chat.completions.create(**req)
                _log_from_resp("chat", req, resp, latency_s=time.time() - _t0, attempt=attempt, stage=self._current_stage)
                return resp
            except APIStatusError as e:
                _log_from_error("chat", req, repr(e), latency_s=time.time() - _t0, attempt=attempt, stage=self._current_stage)
                status = getattr(e, "status_code", None)
                text = getattr(getattr(e, "response", None), "text", "") or ""
                logger.warning(f"APIStatusError {status}: {text[:400]}")
                if status in (429, 500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(backoff ** attempt)
                    continue
                elif status == 400:
                    return "400"
                last_exc = e
                break


            except (APIConnectionError, APIResponseValidationError) as e:
                _log_from_error("chat", req, repr(e), latency_s=time.time() - _t0, attempt=attempt, stage=self._current_stage)
                logger.warning(f"Connection/Validation error: {repr(e)}")
                if attempt < max_retries:
                    time.sleep(backoff ** attempt)
                    continue
                last_exc = e
                break

            except Exception as e:
                _log_from_error("chat", req, repr(e), latency_s=time.time() - _t0, attempt=attempt, stage=self._current_stage)
                logger.warning(f"Unexpected error: {repr(e)}", exc_info=True)
                if attempt < max_retries:
                    time.sleep(backoff ** attempt)
                    continue
                last_exc = e
                break

        if last_exc:
            raise last_exc

    def chat_with_tools_once(
            self,
            *,
            system_prompt: Optional[str],
            user_obj: Dict[str, Any],
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[Any] = "auto",
            model: str = config.MODEL,
            temperature: float = 0.0,
            # an executor: takes one or a list of tool_calls, returns one or many tool messages (dict or list[dict])
            category: Union[str, int],
            execute_tool: Optional[Callable] = None,
            max_rounds: int = config.MAX_ROUNDS,  # max rounds (assistant->tool->assistant is one round)
            max_tool_calls: int = config.MAX_TOOL_CALLS,  # max tool calls per session (safety cap)
            max_tokens: Optional[int] = None,  # override default max_tokens per stage
            **extra
    ) -> Tuple[str, list]:
        """
        Return the full messages array:
        [system, user, assistant(may have tool_calls), tool(...), assistant, tool(...), assistant(final)]
        The final answer is in messages[-1]["content"].
        """

        def _append_if_list(target_list: List[Dict[str, Any]], maybe_list_or_item):
            if maybe_list_or_item is None:
                return
            if isinstance(maybe_list_or_item, list):
                target_list.extend(maybe_list_or_item)
            else:
                target_list.append(maybe_list_or_item)

        # -------- init conversation --------
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            if category == 3:
                messages.append({"role": "system", "content": Prompts.ANSWER_SYSTEM_TOOL_PROMPT3})
            else:
                # [fix] previously hard-coded ANSWER_SYSTEM_TOOL_PROMPT, ignoring the passed system_prompt,
                # so LM's ANSWER_SYSTEM_TOOL_PROMPT_LM (temporal/how-many rules) never took effect. Use the passed value.
                messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": json.dumps(user_obj, ensure_ascii=False)})


        tool_calls_used = 0

        # -------- multi-round loop: assistant -> (tools) -> assistant --------
        for round_id in range(1, max_rounds + 1):
            # 1) get the model reply (collect the full message before executing any tool_call)

            if round_id == max_rounds:
                messages[0]["content"] = Prompts.ANSWER_SYSTEM_PROMPT_FINAL
                messages.append({'role': 'user',
                                 'content': 'This is the final round. You must select the answer mode and output the final answer only. '})
            if (round_id == max_rounds-1) and (category == 2):
                messages.append({'role': 'user',
                                 'content': 'This is the final tool round. You must call query_conversation_time for relevant event. '})
            logger.info(f"---------- input (round {round_id}) ---------")
            # Pass stage-specific max_tokens if provided
            _extra = dict(extra)
            if max_tokens is not None:
                _extra["max_tokens"] = max_tokens
            comp = self.chat_with_tool(
                messages=messages,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                stream=False,  # important: receive the full message first
                # keep if the SDK supports parallel tool calls; ignore otherwise
                parallel_tool_calls=True,
                temperature=temperature,
                **_extra
            )
            if comp == "400":
                return "no information available", []
            if comp is None or not getattr(comp, "choices", None):
                logger.warning(f"LLM returned empty/None choices at round {round_id}, treating as no answer.")
                return "no information available", []
            msg = comp.choices[0].message.model_dump()
            messages.append(msg)

            logger.info(f"---------- output (round {round_id}) ---------")
            logger.info(msg)

            # 2) if the assistant text already gives a JSON answer, try to parse it
            raw_content = msg.get("content") or ""
            try:
                ans_obj = extract_json_from_content(raw_content)
            except Exception as e:
                logger.debug(f"extract_json failed (round {round_id}): {e}; head={raw_content[:200]!r}")
                ans_obj = {"answer": "no information available", "supports": []}

            if isinstance(ans_obj, dict) and ans_obj.get("mode") == "answer":
                # final answer obtained
                logger.info(f"[round {round_id}] final answer: {ans_obj}")
                break

            # 3) if tools are needed and an executor is provided: run all tool_calls
            tool_calls = msg.get("tool_calls") or []
            if tool_calls and execute_tool:
                # accounting and safety cap
                if tool_calls_used + len(tool_calls) > max_tool_calls:
                    # exceeded the safety cap; truncate
                    tool_calls = tool_calls[: max(0, max_tool_calls - tool_calls_used)]
                tool_calls_used += len(tool_calls)

                tool_results_messages: List[Dict[str, Any]] = []

                # execute all tool_calls in one batch; normalize to list[dict]
                batch_result = execute_tool(tool_calls)
                if isinstance(batch_result, list):
                    tool_results = batch_result
                elif isinstance(batch_result, dict):
                    tool_results = [batch_result]
                else:
                    tool_results = []

                # write results (must be role="tool" messages) back into messages
                # if the executor returned only content, wrap it as a standard tool message
                # allow the executor to return full tool messages; otherwise fill them in
                for idx, tc in enumerate(tool_calls):
                    # match the current tool_call's result; tolerate non-1:1 returns from execute_tool
                    r = tool_results[idx] if idx < len(tool_results) else None
                    if r and r.get("role") == "tool" and r.get("tool_call_id"):
                        # already a full tool message
                        tool_results_messages.append(r)
                    else:
                        # wrap
                        content = r if isinstance(r, str) else json.dumps(r or {}, ensure_ascii=False)
                        tool_results_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "name": (tc.get("function") or {}).get("name", "memory_dispatcher"),
                            "content": content
                        })

                # feed back all tool results, then continue to the next round
                _append_if_list(messages, tool_results_messages)

                # next round: let the model decide after seeing the tool results
                tool_choice = "auto"  # keep auto for later rounds
                continue

            # 4) no tool_calls: either it answered (broke above), or it won't call tools anymore
            #    so end the loop and return the current messages.
            logger.info(f"[round {round_id}] no tool_calls; finish.")
            continue

        self.last_tool_calls = tool_calls_used
        return ans_obj.get("answer"), ans_obj.get("supports")

    def _detect_expected_format(self, messages: List[Dict[str, Any]]) -> dict:
        """Inspect the system prompt to guess the expected JSON shape, returning a safe empty default."""
        sys_text = ""
        for m in messages:
            if m.get("role") == "system":
                sys_text = str(m.get("content", ""))
                break
        # ANSWER_SORT_PROMPT: {"mode":"score","relevance_scores":{...}}
        if '"mode"' in sys_text and 'relevance_scores' in sys_text:
            return {"mode": "score", "relevance_scores": {}}
        # ANSWER_SORT_PROMPT2: {"mode":"sort","events":[...]}
        if '"mode"' in sys_text and 'events' in sys_text:
            return {"mode": "sort", "events": []}
        # select_key_tag: expects {"tag_scores": {...}}
        if 'tag_scores' in sys_text:
            return {"tag_scores": {}}
        # generic fallback (rewrite / other structured outputs)
        return {}

    def _repair_json_format(self, messages: List[Dict[str, Any]], raw_text: str, model: str) -> dict:
        """One-shot LLM call to repair a plain-text response into the expected JSON format."""
        expected = self._detect_expected_format(messages)
        repair_prompt = (
            "You are a JSON repair assistant. Below is a system prompt that told you what JSON format to output, "
            "followed by the user input, and then the raw text you actually outputted (which was NOT valid JSON).\n\n"
            f"=== EXPECTED JSON SHAPE ===\n{json.dumps(expected, ensure_ascii=False, indent=2)}\n\n"
            f"=== YOUR RAW OUTPUT ===\n{raw_text[:2000]}\n\n"
            "Reformat your raw output into the expected JSON shape. Output ONLY valid JSON, no explanation."
        )
        try:
            comp = self.chat_with_tool(
                messages=[{"role": "user", "content": repair_prompt}],
                model=model,
                use_tool=False,
                temperature=0.0,
                max_tokens=config.QA_MAX_TOKENS,
            )
            text = ""
            if getattr(comp, "choices", None):
                msg = getattr(comp.choices[0], "message", None)
                if msg is not None:
                    c = msg.content
                    text = ("".join(
                        getattr(p, "text", "") for p in c
                        if getattr(p, "type", "") == "text"
                    ) if isinstance(c, list) else str(c or ""))
            repaired = json.loads(text.strip())
            logger.info(f"chat_text: JSON repair succeeded, head={str(repaired)[:200]!r}")
            return repaired
        except Exception as e:
            logger.warning(f"chat_text: JSON repair also failed: {e}")
            return expected  # return empty-but-correct-format placeholder

    def chat_text(
            self,
            *,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[Any] = "auto",
            model: str = config.MODEL,
            temperature: float = 0.0,
            max_tokens: Optional[int] = None,  # override default per stage
            **extra
    ) -> str:

        if max_tokens is not None:
            extra["max_tokens"] = max_tokens
        max_attempts = config.CHAT_TEXT_PARSE_MAX_ATTEMPTS
        json_out = None
        _last_raw_text = ""

        for attempt in range(max_attempts):

            comp = self.chat_with_tool(
                messages=messages, model=model, tools=tools, tool_choice=tool_choice, use_tool=False,
                temperature=temperature, **extra
            )
            ch0 = comp.choices[0]
            msg = getattr(ch0, "message", None)

            if msg is not None:
                c = msg.content
                if isinstance(c, list):  # rich content structure
                    text = "".join(
                        getattr(p, "text", "") for p in c
                        if getattr(p, "type", "") == "text"
                    )
                else:
                    text = c or ""
            else:
                text = getattr(ch0, "text", "") or ""

            _last_raw_text = text

            try:
                json_out = json.loads(text)
                break
            except json.JSONDecodeError:
                try:
                    json_out = extract_json_from_content(text)
                    break
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"chat_text: failed to parse JSON on attempt {attempt}: {e}")
                    continue

        if json_out is None:
            last_text = (_last_raw_text or "").strip()
            _log_from_error(
                call_type="chat_text_fallback",
                req={"messages_summary": str(messages[-1].get("content", ""))[:500] if messages else ""},
                error=f"chat_text: all parse attempts exhausted (head={last_text[:200]!r})",
                stage=getattr(self, "_current_stage", None),
            )
            if config.ENABLE_JSON_REPAIR:
                logger.warning(
                    f"chat_text: all {max_attempts} parse attempts failed; "
                    f"calling repair LLM (head={last_text[:120]!r})"
                )
                json_out = self._repair_json_format(messages, last_text, model)
            else:
                raise RuntimeError(
                    f"chat_text: all {max_attempts} JSON parse attempts exhausted. "
                    f"stage={getattr(self, '_current_stage', None)}, "
                    f"raw_head={last_text[:300]!r}. "
                    f"Set ENABLE_JSON_REPAIR=1 to enable automatic repair, or check the raw response."
                )

        return json_out






