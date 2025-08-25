from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, List

try:
    from openai import AzureOpenAI
except Exception as _e:
    AzureOpenAI = None

@dataclass
class GenResult:
    text: str
    latency_ms: float
    prompt_chars: int
    output_chars: int
    meta: Dict[str, Any]

class AzureChatModel:
    def __init__(self, name: str, params: Dict[str, Any]):
        if AzureOpenAI is None:
            raise RuntimeError("pip install openai>=1.0 required for Azure OpenAI")
        self.name = name
        self.params = params
        endpoint = params.get("api_base") or params.get("endpoint")
        api_key = params.get("api_key")
        api_version = params.get("api_version", "2024-05-01-preview")
        model = params["model"]
        if not endpoint or not api_key:
            raise RuntimeError(f"AzureChatModel '{name}' missing api_base/api_key.")
        self.client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version=api_version)
        self.model = model

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 2048) -> GenResult:
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(model=self.model, messages=messages)
        t1 = time.perf_counter()
        text = (resp.choices[0].message.content or "").strip()
        prompt_chars = sum(len(m.get("content", "")) for m in messages)
        return GenResult(
            text=text,
            latency_ms=(t1 - t0) * 1000,
            prompt_chars=prompt_chars,
            output_chars=len(text),
            meta={"gcd_used": False, "thinking_enabled": False},  # Azure never uses it here
        )
