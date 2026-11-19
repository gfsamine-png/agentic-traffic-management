"""Phase 5 - Number check: are the numbers in an LLM answer backed by tool results?

A plain-Python safety net against hallucinated numbers. It extracts every number from the
answer and looks for it (allowing normal rounding) in the tool outputs, the system facts or
the user's question. Numbers it cannot find are reported as warnings in the final report.
"""
import re

NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def extract_numbers(text: str):
    return [float(x.replace(",", "")) for x in NUMBER.findall(text or "")]


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 0.051 or abs(a - b) <= 0.005 * max(abs(b), 1e-9)


def unverified_numbers(answer: str, sources: list) -> list:
    known = [abs(n) for src in sources for n in extract_numbers(src)]
    percents = {float(x) for x in PERCENT.findall(answer or "")}
    bad = []
    for n in extract_numbers(answer):
        # small whole numbers (seeds, counts, rounds) are ignored, but a percentage never is
        if n == int(n) and n <= 50 and n not in percents:
            continue
        if not any(_close(n, k) for k in known):
            bad.append(n)
    return sorted(set(bad))