import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers_cfg.grammar_utils import IncrementalGrammarConstraint
from transformers_cfg.generation.logits_process import GrammarConstrainedLogitsProcessor
from transformers_cfg.parser import parse_ebnf
from transformers_cfg.recognizer import StringRecognizer


if __name__ == "__main__":
    # Set device: use GPU if available, else CPU.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Model identifier
    model_id = "Qwen/Qwen2.5-0.5B"

    GRAMMAR_PATH = "grammars/swan_grammar_nath.ebnf"
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_id).to(device)
    model.generation_config.pad_token_id = model.generation_config.eos_token_id


    # Load grammars from file
    with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
        grammar_str = f.read()

    # Create grammars constraint and logits processor
    grammar = IncrementalGrammarConstraint(grammar_str, "root", tokenizer)
    grammar_processor = GrammarConstrainedLogitsProcessor(grammar)

    # Define prompts
    prompts = [
        'Write an equation x + y = c '
    ]

    # Tokenize prompts
    input_ids = tokenizer(prompts, add_special_tokens=False, return_tensors="pt", padding=True)["input_ids"].to(device)

    # Generate constrained text
    output = model.generate(
        input_ids,
        max_new_tokens=50,
        logits_processor=[grammar_processor],
        repetition_penalty=1.1,
        num_return_sequences=1,
    )

    # Decode and print generated text
    generations = tokenizer.batch_decode(output, skip_special_tokens=True)
    for generation in generations:
        print(generation)

# The animal is a cat.