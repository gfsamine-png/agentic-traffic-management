"""Phase 4 - The agent loop: question -> (LLM picks tools -> we run them)* -> final answer.

This is the heart of tool calling. Each round:
  1. the LLM sees the conversation and either asks for tool calls or writes the final answer;
  2. WE execute the requested tools (errors are returned to the LLM so it can correct itself);
  3. the results are appended to the conversation and the LLM is called again.
The loop is bounded (max_rounds) so a confused model cannot loop forever. The trace of
every tool call and result is returned: the dashboard will show it as evidence.
"""
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage


def run_agent(llm, system_prompt, tools, question, max_rounds=4):
    bound = llm.bind_tools(tools)
    by_name = {t.name: t for t in tools}
    messages = [SystemMessage(system_prompt), HumanMessage(question)]
    trace = []

    for round_no in range(1, max_rounds + 1):
        ai = bound.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:                               # the model is done
            return {"answer": ai.content, "trace": trace, "rounds": round_no, "status": "ok"}

        for call in ai.tool_calls:
            tool = by_name.get(call["name"])
            if tool is None:
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
            messages.append(result)
            trace.append({"round": round_no, "tool": call["name"], "args": call["args"],
                          "result": result.content})

    # Tool budget used up: force an answer from what has been collected.
    messages.append(HumanMessage(
        "Tool budget reached. Answer now using only the tool results above."))
    ai = llm.invoke(messages)
    return {"answer": ai.content, "trace": trace, "rounds": max_rounds,
            "status": "budget_exhausted"}