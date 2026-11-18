"""Phase 4 - One place to choose the LLM. Changing the model = changing one line.

The API key is read from the environment variable GROQ_API_KEY, loaded from a file
named .env in the project root (that file is in .gitignore: NEVER commit a key).
"""
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# Open-weight models hosted by Groq. Free-tier limits differ per model (see the Groq console):
#   "openai/gpt-oss-20b"        fast, biggest daily budget -> use while developing
#   "openai/gpt-oss-120b"       stronger tool calling      -> use for the final demo
#   "llama-3.3-70b-versatile"   strong alternative
MODEL = "openai/gpt-oss-20b"


def get_llm(model: str = MODEL):
    # temperature 0 = the most repeatable tool calls.
    # max_retries: Groq answers HTTP 429 when a per-minute limit is hit; the client waits and retries.
    return ChatGroq(model=model, temperature=0, max_retries=4, timeout=60)