# swan-generation

A reproducible benchmark to compare:

- **NL → Swan** code generation
- **Swan Inline** (single-line infill)

across:

- **Azure OpenAI** models (e.g., GPT-4o, o1/o3 via Azure *Chat Completions*)
- **Open-source HF local** models (e.g., Qwen3), with optional **Grammar-Constrained Decoding (GCD)** and **Qwen
  “thinking mode.”**

**The runner:**

- Loads prompt variants from disk (`prompts/<task>/*.txt`)
- Lets you select prompts by name/glob or use all
- Creates timestamped run folders with raw results and a single unified `summary.json`
- Records per-call metadata (e.g., GCD used, thinking mode)

---

## 1) Quick start

```bash
# 1) Create venv + install
python -m venv .venv
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt     # transformers, openai, etc.

# 2) Edit your models (Azure + HF local)
# configs/models.yaml

# 3) Run with all prompts
python -m bench.benchmark_swan \
  --data data/processed/train_all_in_one__swan_inline_with_descriptions.json \
  --models configs/models.yaml \
  --tasks nl2swan,inline \
  --prompts-dir ./prompts \
  --prompt-select-nl2swan all \
  --prompt-select-inline all \
  --output results \
  --num-samples -1
```

Open the printed run folder and check:

- `results.csv` / `results.jsonl` (per-generation rows)

- `summary.json` (unified report grouped by model × task × prompt, with GCD/Thinking usage)

## 2) Repository structure

```
swan-generation/
├─ bench/
│  ├─ benchmark_swan.py           # main CLI
│  ├─ adapters/
│  │  ├─ azure.py                 # Azure OpenAI (Chat Completions)
│  │  └─ hf_local.py              # HF local (Qwen, GCD, thinking mode)
│  ├─ tasks/
│  │  ├─ nl2swan.py               # NL → Swan task
│  │  └─ inline.py                # Swan inline (single missing line)
│  ├─ eval.py                     # exact, token-F1, edit-sim metrics
│  ├─ prompts_loader.py           # loads prompts by name/glob
│  ├─ utils.py                    # helpers (code-fence extraction, timestamps)
│  └─ __init__.py
├─ configs/
│  └─ models.yaml                 # model endpoints & options
├─ data/
│  ├─ processed/
│  │  └─ train_all_in_one__swan_inline_with_descriptions.json
│  └─ example/
│     └─ examples.json
├─ prompts/
│  ├─ nl2swan/                    # one .txt per prompt variant
│  └─ inline/
├─ grammars/
│  └─ grammar_function_node.ebnf  # optional GCD grammar
├─ results/                       # per-run folders (gitignored)
├─ requirements.txt
└─ README.md
```

## 3) Models

Edit `configs/models.yaml` to add your Azure OpenAI endpoints and/or local HF models:

### Azure OpenAI (Chat Completions)

```yaml
- name: azure-gpt4o
  provider: azure-openai
  model: GPT-4o                      # Azure deployment name
  api_base: https://<your-endpoint>.openai.azure.com/
  api_version: 2024-05-01-preview
  api_key: <YOUR_AZURE_OPENAI_KEY>
```

### HF local (Qwen3 with optional GCD and thinking mode)

```yaml
# Qwen3 without thinking
- name: qwen3-4b
  provider: hf-local
  model: Qwen/Qwen3-4B-Instruct
  temperature: 0.0
  top_p: 1.0
  do_sample: false
  max_new_tokens: 256
  use_gcd: false
  enable_thinking: false                # Qwen thinking mode off

# Qwen3 with thinking
- name: qwen3-8b-thinking
  provider: hf-local
  model: Qwen/Qwen3-8B-Instruct
  temperature: 0.0
  top_p: 1.0
  do_sample: false
  max_new_tokens: 256
  use_gcd: true
  grammar_path: ./grammars/grammar_function_node.ebnf
  start_rule: root
  gcd_tasks: [ nl2swan ]
  enable_thinking: true                 # Qwen thinking mode on
```

## 4) Prompts on disk

Place prompt variants as simple text files:

```
prompts/
├─ nl2swan/
│  ├─ base.txt
│  ├─ swan_definitions.md
│  ├─ swan_diagrams.md
│  └─ swan_operator.md
└─ inline/
   ├─ 01_minimal.txt
   ├─ 02_exact_one_line.txt
   └─ 03_no_fences.txt
```

- You can select all, a list by name, or globs per task at run time.

- Empty files and dot/underscore-prefixed files are skipped.

## 5) Run the benchmark

Common flags

- `--data`: path to JSON dataset
- `--models`: path to models config YAML
- `--tasks`: comma-separated tasks to run (`nl2swan`, `inline`)
- `--prompts-dir`: path to prompts folder
- `--prompt-select-<task>`:
    - `all` to use all prompts for the task
    - comma-separated list of prompt names (without `.txt`)
    - globs (e.g., `*_def*.txt`)
- `--num-samples`: number of samples to run per model × task × prompt (default: `-1` = all)
- `--qwen-thinking`: `keep | only | off` (default: `keep`) to override `enable_thinking` per model

#### Examples 

*All prompts for both tasks:*

```bash
python -m bench.benchmark_swan \
  --data data/processed/train_all_in_one__swan_inline_with_descriptions.json \
  --models configs/models.yaml \
  --tasks nl2swan,inline \
  --prompts-dir ./prompts \
  --prompt-select-nl2swan all \
  --prompt-select-inline all \
  --output results \
  --num-samples -1
```

*Pick specific prompt files (order preserved):*

```bash
python -m bench.benchmark_swan \
  --data data/example/examples.json \
  --models configs/models.yaml \
  --tasks nl2swan \
  --prompts-dir ./prompts \
  --prompt-select-nl2swan "swan_operator.md, base.txt"
```

## 6) Grammar-Constrained Decoding (GCD)

Enable in a HF local model entry:

```yaml
use_gcd: true
grammar_path: ./grammars/grammar_function_node.ebnf
start_rule: root
gcd_tasks: [nl2swan]
```

- The adapter passes the **HF tokenizer** to `IncrementalGrammarConstraint`.

- We rebuild the logits processor per generation (avoids state carry-over).

- Ensure your prompt style matches the grammar’s language (e.g., avoid forcing markdown fences if the grammar doesn’t allow backticks).

**How to know it was used?**:
- See `results.csv` columns `gcd_used`, `grammar_path`, `start_rule`.
- See `summary.json` aggregated counts.

## 7) Output files

Each run writes a timestamped folder:

```
results/2025-08-25_14-31-09__tasks-nl2swan-inline__n6__p9999/
├─ run_info.json        # manifest: prompts used, models (sanitized), paths…
├─ results.csv          # per (model × task × prompt × sample) row
├─ results.jsonl        # same, as JSONL
└─ summary.json         # ONE unified report (metrics + run info + GCD/thinking usage)
```

#### `results.csv` columns (key ones)
- `model`, `task`, `prompt_name`, `sample_id`, `name` 
- `pred`, `ref`
- **metrics**: `exact_match`, `token_f1` (NL → Swan only), `edit_sim`
- **perf**: `latency_ms`
- **meta**: `gcd_used`, `thinking_enabled` (if applicable)

#### `summary.json` (**unified report**)

Contains:
- `run` (paths, tasks, prompts used)
- `gcd_models` (HF local model GCD settings)
- `counts` (rows, models, tasks, prompts, samples)
- `grouped`:
  - `by_model_task_prompt`
  - `by_task_prompt_model`
  - `by_model_task`
  - `by_prompt`

Each grouped row includes means for `exact`, `token_f1` (if present), `edit_sim`, `latency_ms`, plus:
- `gcd_used@any`, `gcd_used@ratio`
- `thinking_enabled@any`, `thinking_enabled@ratio`

