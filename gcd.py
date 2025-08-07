import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Optional GCD support
USE_GCD = True
GRAMMAR_PATH = "grammars/equation_toan.ebnf"

if USE_GCD:
    from transformers_cfg.grammar_utils import IncrementalGrammarConstraint
    from transformers_cfg.generation.logits_process import GrammarConstrainedLogitsProcessor


def gen_next_sequence(model, tokenizer, prompt: str, gen_kwargs: dict, enable_thinking: bool) -> str:
    # Handle special tokenization for Qwen models
    if "Qwen" in model.name_or_path:
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=enable_thinking,
        )
        inputs = tokenizer([text], return_tensors="pt").to(model.device)
    else:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    # Optional: apply grammar constraint
    logits_processor = None
    if USE_GCD:
        with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
            grammar_str = f.read()
        grammar = IncrementalGrammarConstraint(grammar_str, "root", tokenizer)
        logits_processor = [GrammarConstrainedLogitsProcessor(grammar)]

    # Generate output
    out = model.generate(
        **inputs,
        **gen_kwargs,
        pad_token_id=tokenizer.eos_token_id,
        logits_processor=logits_processor,
    )

    # Decode generated output (excluding prompt)
    output_text = tokenizer.decode(out[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return output_text


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model_id = "Qwen/Qwen3-8B"  # Change to desired model
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_id).to(device)
    model.generation_config.pad_token_id = tokenizer.pad_token_id

    # Example prompt
    prompts = [
        """Swan Operator Quick Reference:
A Swan operator is either a `node` or a `function`.
Syntax: `kind name (inputs) return (outputs)`
Inputs and outputs are semicolon-separated signals: `name: type`. Optionally use `default = expr` or `last = expr`.
A declaration ends with `;`. A definition includes a scope `{}` with optional `let`, `var`, or `diagram`.

Diagram Definitions:
A diagram describes the operator as interconnected components:
- `expr`: for inputs or constants
- `block`: an operator/function call
- `def`: for outputs
- `wire`: connects outputs to inputs (syntax: `wire <source> => <target1>, <target2>`). Ports are optional and numbered: `#id.(n)`
Each object has a unique ID: `#n`.
All connections must match types, and each input/output port must be connected only once.

Task:
Write a Swan `node` operator using a `diagram` that computes the mean of three `float32` values `a`, `b`, and `c`, and returns the result."""
    ]

    # Run generation
    for prompt in prompts:
        result = gen_next_sequence(
            model,
            tokenizer,
            prompt,
            gen_kwargs={
                "max_new_tokens": 150,
                "repetition_penalty": 1.1,
                "num_return_sequences": 1,
            },
        )
        print("Prompt:\n", prompt)
        print("\nResult:\n", result)
