"""Phase 4 - Check that the Groq LLM can call our tools and answer from real data."""
from langchain_core.messages import HumanMessage
from llm import get_llm
from tools import ANALYSIS_TOOLS

llm = get_llm().bind_tools(ANALYSIS_TOOLS)           # tell the model which tools exist
tools_by_name = {t.name: t for t in ANALYSIS_TOOLS}

question = "Which road is the most congested in the high traffic scenario with the fixed-time controller?"
messages = [HumanMessage(question)]

ai = llm.invoke(messages)                            # 1) the model decides which tool to call
print("Tool calls requested by the model:", ai.tool_calls)
messages.append(ai)
for call in ai.tool_calls:                           # 2) WE run the real Python function
    messages.append(tools_by_name[call["name"]].invoke(call))

final = llm.invoke(messages)                         # 3) the model explains the real result
print("\nFinal answer:\n", final.content)
print("\nTokens used (watch the per-minute limit):", final.usage_metadata)