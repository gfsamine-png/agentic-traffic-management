"""Phase 4 - The agent loop: question -> (LLM picks tools -> we run them)* -> final answer.

This is the heart of tool calling. Each round:
  1. the LLM sees the conversation and either asks for tool calls or writes the final answer;
  2. WE execute the requested tools (errors are returned to the LLM so it can correct itself);
  3. the results are appended to the conversation and the LLM is called again.
The loop is bounded (max_rounds) so a confused model cannot loop forever. The trace of
every tool call and result is returned: the dashboard will show it as evidence.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

MAX_INVALID_CALLS = 2     # how many malformed tool calls we forgive before giving up


def _is_bad_tool_call(exc) -> bool:
    """The API itself refused the model's tool call (missing/wrong arguments)."""
    text = str(exc).lower()
    return "tool_use_failed" in text or "tool call validation failed" in text


def run_agent(llm, system_prompt, tools, question, max_rounds=4):
    bound = llm.bind_tools(tools)
    by_name = {t.name: t for t in tools}
    messages = [SystemMessage(system_prompt), HumanMessage(question)]
    trace = []
    invalid = 0
    seen = set()                 # (tool, arguments) already called in this run

    for round_no in range(1, max_rounds + 1):
        try:
            ai = bound.invoke(messages)
        except Exception as exc:
            if not _is_bad_tool_call(exc):
                raise                                       # real problem (key, network...)
            # The model produced a malformed tool call and the API rejected it.
            # Tell the model what was wrong and let it try again.
            invalid += 1
            trace.append({"round": round_no, "tool": "(invalid tool call)", "args": {},
                          "result": f"rejected by the API: {str(exc)[:300]}"})
            if invalid > MAX_INVALID_CALLS:
                return {"answer": "The model could not produce a valid tool call, so this "
                                  "step was stopped. Please retry, or use a stronger model "
                                  "(the larger gpt-oss model).",
                        "trace": trace, "rounds": round_no, "status": "tool_call_failed"}
            messages.append(HumanMessage(
                "Your last tool call was rejected because it did not match the tool's "
                "schema (a required argument was missing or wrong). Call the tool again and "
                f"give ALL required arguments. Details: {str(exc)[:300]}"))
            continue
        messages.append(ai)
        if not ai.tool_calls:                               # the model is done
            cut = (ai.response_metadata or {}).get("finish_reason") == "length"
            return {"answer": ai.content, "trace": trace, "rounds": round_no,
                    "status": "truncated" if cut else "ok"}

        for call in ai.tool_calls:
            tool = by_name.get(call["name"])
            key = (call["name"], json.dumps(call["args"], sort_keys=True, default=str))
            if key in seen:
                result = ToolMessage(
                    content="Duplicate call: you already made this exact call. Do not repeat "
                            "it: use the earlier result, or explain that it failed.",
                    tool_call_id=call["id"], name=call["name"], status="error")
            elif tool is None:
                result = ToolMessage(
                    content=f"Unknown tool '{call['name']}'. Available: {list(by_name)}",
                    tool_call_id=call["id"], name=call["name"], status="error")
            else:
                try:
                    result = tool.invoke(call)              # runs the real Python function
                except Exception as exc:                    # bad arguments etc.: tell the model
                    result = ToolMessage(content=f"Tool error: {exc}",
                                         tool_call_id=call["id"], name=call["name"],
                                         status="error")
            seen.add(key)
            messages.append(result)
            trace.append({"round": round_no, "tool": call["name"], "args": call["args"],
                          "result": result.content})

    # Tool budget used up: force an answer from what has been collected.
    # The model may still try to call a tool (Groq then answers HTTP 400 'tool_use_failed'),
    # so we tolerate that and ask again, then fall back to a plain message.
    messages.append(HumanMessage(
        "Tool budget reached. Do NOT call any tool. Write the final answer now, in plain "
        "text, using only the tool results above."))
    answer = ""
    for _ in range(3):
        try:
            ai = llm.invoke(messages)
        except Exception as exc:
            if not _is_bad_tool_call(exc):
                raise
            messages.append(HumanMessage(
                "No tools are available any more. Reply with the final answer in plain text."))
            continue
        if ai.content and ai.content.strip():
            answer = ai.content
            break
        messages.append(ai)
        messages.append(HumanMessage("Reply with the final answer in plain text, no tool call."))
    if not answer:
        answer = ("The model did not manage to write a final answer after using its tool "
                  "budget. The tool results are listed in the evidence below.")
    return {"answer": answer, "trace": trace, "rounds": max_rounds,
            "status": "budget_exhausted"}