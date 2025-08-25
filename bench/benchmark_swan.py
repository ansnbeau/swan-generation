import argparse
import csv
import json
import sys
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

# utils & eval
from .utils import timestamped_run_dir
from .eval import eval_nl2swan, eval_inline
from .prompts_loader import load_prompts_for_task

# adapters
from .adapters.azure import AzureChatModel as AzureModel  # chat-like
from .adapters.hf_local import HFLocalModel as HFModel    # local HF (optional GCD)

# tasks
from .tasks import nl2swan as task_nl2swan
from .tasks import inline as task_inline


@dataclass
class Sample:
    id: str
    name: str
    nl_description: str
    swan: str
    c_code: str
    inline: Dict[str, Any]


def load_samples(path: str) -> List[Sample]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: List[Sample] = []
    for it in data:
        out.append(Sample(
            id=it["id"],
            name=it["name"],
            nl_description=it["nl_description"],
            swan=it["swan"],
            c_code=it.get("c_code", ""),
            inline=it["inline"],
        ))
    return out


def build_model_adapter(entry: Dict[str, Any]):
    provider = entry.get("provider", "azure-openai")
    name = entry.get("name") or f"{provider}:{entry.get('model')}"
    if provider == "azure-openai":
        return AzureModel(name=name, params=entry)
    elif provider == "hf-local":
        return HFModel(name=name, params=entry)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Path to dataset JSON (with nl_description + inline)")
    ap.add_argument("--models", required=True, help="YAML list of model configs")
    ap.add_argument("--tasks", default="nl2swan,inline", help="Tasks: nl2swan,inline")
    ap.add_argument("--prompts-dir", default="./prompts", help="Folder with <task> subfolders of prompt .txt/.md files")
    ap.add_argument("--output", default="./results", help="Parent output folder (per-run subfolder created)")
    ap.add_argument("--max-prompts", type=int, default=4, help="Max prompt variants to use per task (ignored if explicit selection list/glob is used)")
    # Per-task prompt selection specs
    ap.add_argument("--prompt-select-nl2swan", default="", help="Prompt selection for nl2swan: 'all' or comma list of names/globs (e.g. '01_minimal.txt,03_no_comments.txt' or '02_*').")
    ap.add_argument("--prompt-select-inline", default="", help="Prompt selection for inline: 'all' or comma list of names/globs.")
    ap.add_argument("--num-samples", type=int, default=-1, help="Limit number of samples (-1=all)")
    ap.add_argument(
        "--qwen-thinking",
        choices=["keep", "on", "off"],
        default="keep",
        help="For hf-local Qwen models only: enable/disable thinking chat template. "
             "'keep' uses models.yaml as-is.",
    )
    args = ap.parse_args()

    # Load model configs and initialize adapters
    model_cfgs = yaml.safe_load(Path(args.models).read_text(encoding="utf-8")) or []
    for cfg in model_cfgs:
        if cfg.get("provider") == "hf-local" and "Qwen" in str(cfg.get("model", "")):
            if args.qwen_thinking == "on":
                cfg["enable_thinking"] = True
            elif args.qwen_thinking == "off":
                cfg["enable_thinking"] = False
    adapters = []
    for cfg in model_cfgs:
        try:
            adapters.append(build_model_adapter(cfg))
        except Exception as e:
            print(f"[error] could not init model {cfg.get('name')}: {e}", file=sys.stderr)
    if not adapters:
        print("[fatal] no models initialized; check models.yaml", file=sys.stderr)
        sys.exit(1)

    # Tasks
    tasks = [t.strip().lower() for t in args.tasks.split(",") if t.strip()]

    # Load prompts per task (with selection)
    selection_specs = {
        "nl2swan": args.prompt_select_nl2swan,
        "inline": args.prompt_select_inline,
    }
    prompts_used: Dict[str, Dict[str, Any]] = {}
    task_prompts: Dict[str, List[str]] = {}
    for t in tasks:
        plist, fnames = load_prompts_for_task(
            task=t,
            root=args.prompts_dir,
            max_prompts=args.max_prompts,
            select_spec=selection_specs.get(t, ""),
        )
        task_prompts[t] = plist
        prompts_used[t] = {
            "count": len(plist),
            "files": fnames,
            "select_spec": selection_specs.get(t, ""),
        }
        if not plist:
            print(f"[warn] no prompts selected for task '{t}' (dir={args.prompts_dir}/{t})", file=sys.stderr)

    # Load samples
    samples = load_samples(args.data)
    if args.num_samples > 0:
        samples = samples[:args.num_samples]

    # Per-run folder (timestamped)
    slug = f"tasks-{'-'.join(tasks)}__n{len(samples)}__p{args.max_prompts}"
    out_dir = timestamped_run_dir(Path(args.output), slug)

    # Save run_info manifest
    sanitized_models = [{"name": m.get("name"), "provider": m.get("provider"), "model": m.get("model")} for m in model_cfgs]
    (out_dir / "run_info.json").write_text(json.dumps({
        "data": str(Path(args.data).resolve()),
        "models_file": str(Path(args.models).resolve()),
        "tasks": tasks,
        "prompts_dir": str(Path(args.prompts_dir).resolve()),
        "prompts_used": prompts_used,
        "max_prompts": args.max_prompts,
        "actual_num_samples": len(samples),
        "models": sanitized_models,
        "model_names": [a.name for a in adapters],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Run benchmark
    rows: List[Dict[str, Any]] = []
    for smp in samples:
        for mdl in adapters:
            chat_like = isinstance(mdl, AzureModel)  # Azure adapter uses chat messages API
            for task in tasks:
                try:
                    plist = task_prompts.get(task, [])
                    fnames = (prompts_used.get(task) or {}).get("files", [])
                    if not plist:
                        continue

                    # Debug line (optional)
                    # print(f"[run] task={task} model={mdl.name} sample={smp.id} prompts={len(plist)} -> {fnames}")

                    if task == "nl2swan":
                        for i, phr in enumerate(plist, 1):
                            res = task_nl2swan.run(mdl, smp.nl_description, phr, chat_like)
                            scores = eval_nl2swan(res.text, smp.swan)
                            rows.append({
                                "sample_id": smp.id, "name": smp.name, "task": task, "prompt_idx": i,
                                "prompt_name": fnames[i-1] if i-1 < len(fnames) else "",
                                "model": mdl.name, "provider": mdl.params.get("provider"),
                                "pred": res.text, "ref": smp.swan,
                                "latency_ms": round(res.latency_ms, 2),
                                "prompt_chars": res.prompt_chars, "output_chars": res.output_chars,
                                "gcd_used": bool(res.meta.get("gcd_used", False)),
                                "grammar_path": res.meta.get("grammar_path"),
                                "start_rule": res.meta.get("start_rule"),
                                "thinking_enabled": bool(res.meta.get("thinking_enabled", False)),
                                **scores
                            })

                    elif task == "inline":
                        ref_line = smp.inline["target"]
                        for i, phr in enumerate(plist, 1):
                            res = task_inline.run(mdl, smp.inline["prefix"], smp.inline["suffix"], phr, chat_like)
                            scores = eval_inline(res.text, ref_line)
                            rows.append({
                                "sample_id": smp.id, "name": smp.name, "task": task, "prompt_idx": i,
                                "prompt_name": fnames[i-1] if i-1 < len(fnames) else "",
                                "model": mdl.name, "provider": mdl.params.get("provider"),
                                "pred": res.text, "ref": ref_line,
                                "latency_ms": round(res.latency_ms, 2),
                                "prompt_chars": res.prompt_chars, "output_chars": res.output_chars,
                                "gcd_used": bool(res.meta.get("gcd_used", False)),
                                "grammar_path": res.meta.get("grammar_path"),
                                "start_rule": res.meta.get("start_rule"),
                                **scores
                            })

                    else:
                        print(f"[warn] unknown task: {task}", file=sys.stderr)

                except Exception as e:
                    print(f"[warn] task {task} failed for model {mdl.name} sample {smp.id}: {e}", file=sys.stderr)

    # Write per-generation results
    csv_path = out_dir / "results.csv"
    jsonl_path = out_dir / "results.jsonl"
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    else:
        csv_path.write_text("", encoding="utf-8")
        jsonl_path.write_text("", encoding="utf-8")

    # ─────────────────────────────────────────────────────────────────────────
    # Unified summary.json (includes run info + grouped views + GCD info)
    # ─────────────────────────────────────────────────────────────────────────
    from statistics import mean

    def _safe_prompt_name(r: Dict[str, Any]) -> str:
        return r.get("prompt_name") or f"prompt_{r.get('prompt_idx', '?')}"

    def _aggregate(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
        buckets: Dict[tuple, List[Dict[str, Any]]] = {}
        for r in rows:
            vals = []
            for k in keys:
                if k == "prompt_name":
                    vals.append(_safe_prompt_name(r))
                else:
                    vals.append(r.get(k))
            key = tuple(vals)
            buckets.setdefault(key, []).append(r)

        out: List[Dict[str, Any]] = []
        for key_tuple, rr in buckets.items():
            item = {k: v for k, v in zip(keys, key_tuple)}
            item.update({
                "n": len(rr),
                "exact@mean": round(mean(x["exact"] for x in rr), 3),
                "edit_sim@mean": round(mean(x["edit_sim"] for x in rr), 3),
                "latency_ms@mean": round(mean(x["latency_ms"] for x in rr), 1),
                "gcd_used": bool(res.meta.get("gcd_used", False)),
                "grammar_path": res.meta.get("grammar_path"),
                "start_rule": res.meta.get("start_rule"),
                "thinking_enabled": bool(res.meta.get("thinking_enabled", False)),

            })
            if any("token_f1" in x for x in rr):
                item["token_f1@mean"] = round(mean(x.get("token_f1", 0.0) for x in rr), 3)
            out.append(item)

        return sorted(out, key=lambda d: tuple(d[k] for k in keys))

    # Build grouped views
    by_model_task_prompt = _aggregate(rows, ["model", "task", "prompt_name"])
    by_task_prompt_model = _aggregate(rows, ["task", "prompt_name", "model"])
    by_model_task = _aggregate(rows, ["model", "task"])
    by_prompt = _aggregate(rows, ["prompt_name"])

    # Build a unified report with run info included
    run_info = {
        "data": str(Path(args.data).resolve()),
        "models_file": str(Path(args.models).resolve()),
        "tasks": tasks,
        "prompts_dir": str(Path(args.prompts_dir).resolve()),
        "prompts_used": prompts_used,
        "max_prompts": args.max_prompts,
        "actual_num_samples": len(samples),
        "models": sanitized_models,
        "model_names": [a.name for a in adapters],
        "results_csv": str(csv_path.resolve()),
        "results_jsonl": str(jsonl_path.resolve()),
    }

    # Pull model-level GCD settings into the report (sanitized)
    gcd_models = []
    for cfg in model_cfgs:
        if cfg.get("provider") == "hf-local":
            gcd_models.append({
                "name": cfg.get("name"),
                "model": cfg.get("model"),
                "use_gcd": bool(cfg.get("use_gcd", False)),
                "grammar_path": cfg.get("grammar_path"),
                "start_rule": cfg.get("start_rule"),
                "gcd_tasks": cfg.get("gcd_tasks", []),
            })

    unified = {
        "run": run_info,
        "gcd_models": gcd_models,
        "counts": {
            "rows": len(rows),
            "models": len(adapters),
            "tasks": len(tasks),
            "prompts": {t: prompts_used[t]["count"] for t in prompts_used},
            "samples": len(samples),
        },
        "grouped": {
            "by_model_task_prompt": by_model_task_prompt,
            "by_task_prompt_model": by_task_prompt_model,
            "by_model_task": by_model_task,
            "by_prompt": by_prompt,
        },
    }

    (out_dir / "summary.json").write_text(json.dumps(unified, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Run folder:", out_dir.resolve())
    print(f"Wrote:\n- {csv_path}\n- {jsonl_path}\n- {out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
