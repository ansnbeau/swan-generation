import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers_cfg.grammar_utils import IncrementalGrammarConstraint
from transformers_cfg.generation.logits_process import GrammarConstrainedLogitsProcessor


def gen_next_sequence(
    model,
    tokenizer,
    prompt_template,
    history,
    gen_kwargs,
    style,
) -> str:
    prompt = prompt_template.format(history="\n".join(history))
    if model.name_or_path == "Qwen/Qwen3-4B" or model.name_or_path == "Qwen/Qwen3-8B":
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,  # Switches between thinking and non-thinking modes. Default is True.
        )
        inputs = tokenizer([text], return_tensors="pt").to(model.device)
    else:
        inputs = tokenizer(
            prompt, return_tensors="pt", truncation=True, padding=True
        ).to(model.device)

    # Define grammar string
    GRAMMAR_PATH = "grammars/equation_toan_rec.ebnf"

    # Load grammars from file
    with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
        grammar_str = f.read()

    # Create grammar constraint and logits processor
    grammar = IncrementalGrammarConstraint(grammar_str, "root", tokenizer)
    grammar_processor = GrammarConstrainedLogitsProcessor(grammar)

    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    out = model.generate(
        **inputs,
        **gen_kwargs,
        pad_token_id=tokenizer.eos_token_id,
        logits_processor=[grammar_processor],
    )
    raw = tokenizer.decode(
        out[0, inputs["input_ids"].shape[-1] :], skip_special_tokens=True
    )
    return raw


if __name__ == "__main__":
    # Set device: use GPU if available, else CPU.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Model identifier
    model_id = "Qwen/Qwen3-4B"  # google-t5/t5-base Qwen/Qwen3-1.7B TinyLlama/TinyLlama_v1.1 microsoft/Phi-3-mini-4k-instruct meta-llama/Meta-Llama-3-8B
    max_new_tokens = 50
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_id).to(device)
    model.generation_config.pad_token_id = tokenizer.pad_token_id

    # Define prompts
    prompts = [
        "Write an equation of x + y = c: ",
        "Write an expression where variable c is an addition of two variables x and y: ",
        "Write a calculation for the sum of two numbers: ",
        "Write a calculation for the difference of two numbers: ",
        "Write a calculation for the product of two numbers: ",
        "Write an 'AND' logical expression for a, b and c variables: ",
        "Write a calculation for the division of two numbers: ",
    ]

    for prompt in prompts:
        # Generate constrained text
        output = gen_next_sequence(
            model=model,
            tokenizer=tokenizer,
            prompt_template=prompt,
            history=[],
            gen_kwargs={
                "max_new_tokens": max_new_tokens,
                "repetition_penalty": 1.1,
                "num_return_sequences": 1,
            },
            style=None,
        )
        print(f"Result: {output}")
