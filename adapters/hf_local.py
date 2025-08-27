from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

# Optional GCD
CFG_AVAILABLE = False
try:
    from transformers_cfg.grammar_utils import IncrementalGrammarConstraint
    from transformers_cfg.generation.logits_process import GrammarConstrainedLogitsProcessor
    CFG_AVAILABLE = True
except Exception:
    CFG_AVAILABLE = False

from utils import extract_code_block, first_nonempty_line

@dataclass
class GenResult:
    text: str
    latency_ms: float
    prompt_chars: int
    output_chars: int
    meta: Dict[str, Any]  # includes gcd_used + thinking_enabled

def _apply_chat_template_if_needed(model, tokenizer, prompt: str, enable_thinking: bool):
    name = getattr(model, "name_or_path", "")
    if "Qwen" in str(name):
        messages = [{"role": "user", "content": prompt}]
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=enable_thinking,  # <-- thinking flag (Qwen only)
            )
        except TypeError:
            # Older tokenizers without enable_thinking: fall back gracefully
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
    return prompt


def _build_logits_processors(use_gcd: bool, grammar_path: Optional[str], start_rule: Optional[str], tokenizer):
    if not use_gcd:
        return None, None
    if not CFG_AVAILABLE:
        print("[WARN] transformers_cfg not available; running without grammar.")
        return None, None
    if not grammar_path or not start_rule:
        print("[WARN] use_gcd requested but grammar_path/start_rule missing.")
        return None, None

    text = Path(grammar_path).read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.endswith("\n"):
        text += "\n"

    grammar = IncrementalGrammarConstraint(text, start_rule, tokenizer)
    processors = [GrammarConstrainedLogitsProcessor(grammar)]
    return processors, grammar

class HFLocalModel:
    """
    params:
      model: HF repo id
      do_sample, top_p, repetition_penalty, max_new_tokens
      use_gcd: bool
      grammar_path: str
      start_rule: str
      gcd_tasks: list[str]  (defaults to ["nl2swan"])
      enable_thinking: bool (Qwen option)
    """
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self._load()
        # Config only; processors are built PER GENERATION to avoid state carry-over
        self.use_gcd = bool(params.get("use_gcd", False))
        self.grammar_path = params.get("grammar_path")
        self.start_rule = params.get("start_rule", "root")
        self.gcd_tasks = [t.lower() for t in params.get("gcd_tasks", ["nl2swan"])]
        self.enable_thinking = bool(params.get("enable_thinking", False))

    def _load(self):
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as e:
            raise RuntimeError("pip install transformers torch required for hf-local") from e
        model_id = self.params["model"]
        trust = self.params.get("trust_remote_code", True)
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=trust)
        if self.tokenizer.pad_token is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=trust, torch_dtype="auto")
        self.model.eval()
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(device)
            self.model.generation_config.pad_token_id = self.tokenizer.pad_token_id
        except Exception:
            pass

    def _gen_kwargs(self, max_tokens: int) -> Dict[str, Any]:
        return dict(
            max_new_tokens=int(self.params.get("max_new_tokens", max_tokens)),
            do_sample=bool(self.params.get("do_sample", False)),
            repetition_penalty=float(self.params.get("repetition_penalty", 1.0)),
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
        )

    def generate_for_task(self, prompt: str, task: str, max_tokens: int = 2048) -> GenResult:
        import torch
        use_gcd_now = self.use_gcd and (task.lower() in self.gcd_tasks)

        # Chat template (Qwen, etc.)
        text = _apply_chat_template_if_needed(self.model, self.tokenizer, prompt, self.enable_thinking)
        inputs = self.tokenizer(text, return_tensors="pt")
        if hasattr(self.model, "device"):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        gen_kwargs = self._gen_kwargs(max_tokens)

        # Build FRESH processors per generation when GCD is enabled
        if use_gcd_now:
            lp, _ = _build_logits_processors(True, self.grammar_path, self.start_rule, self.tokenizer)
            if lp is not None:
                gen_kwargs["logits_processor"] = lp

        t0 = time.perf_counter()
        with torch.inference_mode():
            out_ids = self.model.generate(**inputs, **gen_kwargs)
        t1 = time.perf_counter()

        out = self.tokenizer.decode(out_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return GenResult(
            text=out,
            latency_ms=(t1 - t0) * 1000,
            prompt_chars=len(prompt),
            output_chars=len(out),
            meta={
                "gcd_used": bool(use_gcd_now),
                "grammar_path": self.grammar_path if use_gcd_now else None,
                "start_rule": self.start_rule if use_gcd_now else None,
                "gcd_tasks": self.gcd_tasks,
                "thinking_enabled": bool(
                    self.enable_thinking and "Qwen" in str(getattr(self.model, "name_or_path", ""))),
            },
        )

    # Back-compat
    def generate(self, prompt: str, max_tokens: int = 2048) -> GenResult:
        return self.generate_for_task(prompt, task="generic", max_tokens=max_tokens)
