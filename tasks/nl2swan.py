from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from utils import extract_code_block

@dataclass
class GenResult:
    text: str
    latency_ms: float
    prompt_chars: int
    output_chars: int
    meta: Dict[str, Any]  # NEW

def messages_for_chat(system: str | None, user: str) -> List[Dict[str, str]]:
    msgs = []
    if system: msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    return msgs

def run(model, nl_description: str, prompt_variant: str, chat_like: bool) -> GenResult:
    user = f"""{prompt_variant}

Description:
{nl_description}
"""
    if hasattr(model, "generate") and chat_like:
        msgs = messages_for_chat(system="You are a precise Swan code generator.", user=user)
        res = model.generate(msgs)
        code = extract_code_block(res.text, "swan")
        return GenResult(code, res.latency_ms, res.prompt_chars, len(code), getattr(res, "meta", {}) or {})
    else:
        # HF local path
        if hasattr(model, "generate_for_task"):
            res = model.generate_for_task(user + "\n\n### Response:\n", task="nl2swan")
        else:
            res = model.generate(user + "\n\n### Response:\n")
        code = extract_code_block(res.text, "swan")
        return GenResult(code, res.latency_ms, res.prompt_chars, len(code), getattr(res, "meta", {}) or {})
