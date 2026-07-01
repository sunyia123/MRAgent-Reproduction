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
import logging
logger = logging.getLogger(__name__)

# --- Diagnostic logging (activated by DIAGNOSTIC_LOG=1 in .env) ---
_DIAG_ENABLED = os.getenv("DIAGNOSTIC_LOG", "0") == "1"
_DIAG_DIR = os.path.join("result", "diagnostics")
if _DIAG_ENABLED:
    os.makedirs(_DIAG_DIR, exist_ok=True)
    _diag_logger = logging.getLogger("llm.diagnostics")
    _diag_logger.setLevel(logging.DEBUG)
    _diag_fh = logging.FileHandler(os.path.join(_DIAG_DIR, "raw_api_calls.jsonl"), encoding="utf-8")
    _diag_fh.setLevel(logging.DEBUG)
    _diag_fh.setFormatter(logging.Formatter('%(message)s'))
    _diag_logger.addHandler(_diag_fh)
    _diag_logger.propagate = False
    logger.info(f"Diagnostic logging enabled → {os.path.join(_DIAG_DIR, 'raw_api_calls.jsonl')}")


def _diag_record(call_type: str, request: dict, response: Any, error: Optional[str] = None,
                 latency_s: float = 0.0, attempt: int = 1):
    """Record a raw API call to the diagnostic log (only when DIAGNOSTIC_LOG=1)."""
    if not _DIAG_ENABLED:
        return
    try:
        rec = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "call_type": call_type,  # "chat" or "embedding"
            "attempt": attempt,
            "latency_s": round(latency_s, 3),
            "request": {
                "model": request.get("model"),
                "messages_count": len(request.get("messages", [])),
                "messages_summary": _summarize_messages(request.get("messages", [])),
                "temperature": request.get("temperature"),
                "max_tokens": request.get("max_tokens"),
                "tools_count": len(request.get("tools", [])),
            },
        }
        if response is not None:
            try:
                choice = response.choices[0]
                msg = getattr(choice, "message", None)
                rec["response"] = {
                    "finish_reason": getattr(choice, "finish_reason", None),
                    "content_length": len(getattr(msg, "content", "") or ""),
                    "content_preview": (getattr(msg, "content", "") or "")[:500],
                    "tool_calls_count": len(getattr(msg, "tool_calls", []) or []),
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "function": getattr(tc, "function", None).name if hasattr(tc, "function") else None,
                            "arguments_preview": (getattr(getattr(tc, "function", None), "arguments", "") or "")[:300],
                        }
                        for tc in (getattr(msg, "tool_calls", []) or [])
                    ],
                }
                usage = getattr(response, "usage", None)
                if usage:
                    rec["response"]["usage"] = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", None),
                        "completion_tokens": getattr(usage, "completion_tokens", None),
                        "total_tokens": getattr(usage, "total_tokens", None),
                    }
                # Include model identifier from response
                rec["response"]["model"] = getattr(response, "model", None)
            except Exception as e:
                rec["response_parse_error"] = str(e)[:200]
        if error:
            rec["error"] = error[:1000]
            rec["error_type"] = type(error).__name__
        _diag_logger.info(json.dumps(rec, ensure_ascii=False, default=str))
    except Exception:
        pass  # diagnostic logging must never crash the pipeline


def _summarize_messages(messages: list) -> list:
    """Create a compact summary of messages for diagnostic purposes."""
    summary = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "") or ""
        if isinstance(content, str):
            clen = len(content)
            summary.append({
                "role": role,
                "content_length": clen,
                "content_hash": hashlib.md5(content.encode()).hexdigest()[:8] if clen > 0 else "",
                "content_preview": content[:200] + ("..." if clen > 200 else ""),
            })
        elif isinstance(content, list):
            summary.append({"role": role, "content_type": "multipart", "parts": len(content)})
        else:
            summary.append({"role": role, "content_type": type(content).__name__})
        # tool_call_id for tool messages
        if m.get("tool_call_id"):
            summary[-1]["tool_call_id"] = m["tool_call_id"][:16]
        if m.get("name"):
            summary[-1]["name"] = m["name"]
    return summary

class LLM:
    def __init__(self):
        self.client = OpenAI(api_key=config.API_KEY,
                             base_url=config.LLM_BASE_URL,
                             timeout=600.0,
                             max_retries=2)
        self.model = config.MODEL
        # metrics instrumentation
        self.last_tool_calls = 0

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
            max_retries: int = 3,
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
        # Guard: prevent unbounded generation on slow providers
        if "max_tokens" not in req:
            req["max_tokens"] = 4096

        last_exc: Optional[Exception] = None
        _t0 = 0.0
        for attempt in range(1, max_retries + 1):
            try:
                _t0 = time.time()
                resp =  self.client.chat.completions.create(**req)
                _diag_record("chat", req, resp, latency_s=time.time() - _t0, attempt=attempt)
                return resp
            except APIStatusError as e:
                _diag_record("chat", req, None, error=repr(e), latency_s=time.time() - _t0, attempt=attempt)
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
                _diag_record("chat", req, None, error=repr(e), latency_s=time.time() - _t0, attempt=attempt)
                logger.warning(f"Connection/Validation error: {repr(e)}")
                if attempt < max_retries:
                    time.sleep(backoff ** attempt)
                    continue
                last_exc = e
                break

            except Exception as e:
                _diag_record("chat", req, None, error=repr(e), latency_s=time.time() - _t0, attempt=attempt)
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
            comp = self.chat_with_tool(
                messages=messages,
                model=model,
                tools=tools,
                tool_choice=tool_choice,
                stream=False,  # important: receive the full message first
                # keep if the SDK supports parallel tool calls; ignore otherwise
                parallel_tool_calls=True,
                temperature=temperature,
                **extra
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

    def chat_text(
            self,
            *,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[Any] = "auto",
            model: str = config.MODEL,
            temperature: float = 0.0,
            **extra
    ) -> str:

        max_attempts = 3
        json_out = None

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

            try:
                json_out = json.loads(text)
                break
            except json.JSONDecodeError:
                try:
                    json_out = extract_json_from_content(text)
                    break
                except (json.JSONDecodeError, ValueError) as e:
                    # log the error and keep retrying even if parsing fails
                    logger.warning(f"chat_text: failed to parse JSON on attempt {attempt}: {e}")
                    continue
        return json_out






