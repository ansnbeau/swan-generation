from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
from ..utils import first_nonempty_line

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

def run(model, prefix: str, suffix: str, prompt_variant: str, chat_like: bool) -> GenResult:
    user = f"""{prompt_variant}

Prefix:
{prefix.rstrip()}
Suffix:
{suffix.lstrip()}
Return only the single missing Swan line."""
    if hasattr(model, "generate") and chat_like:
        msgs = messages_for_chat(system="You perform single-line Swan completion.", user=user)
        res = model.generate(msgs, max_tokens=128)
    else:
        prompt = f"{user}\n\n### Missing line:\n"
    if hasattr(model, "generate_for_task"):
        res = model.generate_for_task(prompt, task="inline", max_tokens=128)
    else:
        res = model.generate(prompt, max_tokens=128)
    line = first_nonempty_line(res.text, lang_hint="swan")
    return GenResult(line, res.latency_ms, res.prompt_chars, len(line), getattr(res, "meta", {}) or {})
