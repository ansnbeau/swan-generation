from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional
import fnmatch

def _select_prompt_files(files: List[Path], select_spec: Optional[str]) -> List[Path]:
    """
    Select files based on a user spec:
      - None or "": return files (sorted) as-is
      - "all": return all files (sorted)
      - comma-separated list of names or globs, e.g.:
          "01_minimal.txt, 03_no_fences.txt"
          "02_*, 04_concise.txt"
        Matching is case-insensitive, and bare stems (without extension) are allowed.
        Order is exactly the order given in the spec.
    """
    files_sorted = sorted(files, key=lambda p: p.name.lower())
    if not select_spec or not select_spec.strip():
        return files_sorted

    spec = select_spec.strip()
    if spec.lower() == "all":
        return files_sorted

    items = [x.strip() for x in spec.split(",") if x.strip()]
    picked: List[Path] = []
    seen = set()

    def add_match(p: Path):
        key = p.resolve()
        if key not in seen:
            seen.add(key)
            picked.append(p)

    # Build lowercase name maps for exact/base matches
    by_name = {p.name.lower(): p for p in files_sorted}
    by_stem = {p.stem.lower(): p for p in files_sorted}

    for it in items:
        it_l = it.lower()
        # glob if wildcard
        if any(ch in it for ch in "*?[]"):
            matches = [p for p in files_sorted if fnmatch.fnmatch(p.name.lower(), it_l)]
            if matches:
                for p in matches:
                    add_match(p)
            else:
                print(f"[warn] prompt pattern '{it}' did not match any files")
            continue

        # exact filename first
        if it_l in by_name:
            add_match(by_name[it_l])
            continue

        # base name (no extension)
        if it_l in by_stem:
            add_match(by_stem[it_l])
            continue

        print(f"[warn] prompt name '{it}' not found (no match by name or stem)")

    return picked

def load_prompts_for_task(
    task: str,
    root: str,
    max_prompts: int | None = None,
    select_spec: Optional[str] = None,
) -> Tuple[list[str], list[str]]:
    """
    Load prompt texts for a task from folder: <root>/<task>/*.txt (or .md).
    Returns (prompts, filenames) ordered by selection logic:
      - If select_spec is:
          * None/"" : sorted by filename; truncated by max_prompts (if given)
          * "all"   : all files (sorted); truncated by max_prompts (if given)
          * list    : exact order per list/patterns; max_prompts is ignored
    """
    task = task.lower().strip()
    base = Path(root) / task
    if not base.exists():
        return [], []

    all_files = sorted(
        p for p in base.iterdir()
        if p.is_file()
        and not p.name.startswith((".", "_"))
        and p.suffix.lower() in {".txt", ".md"}
    )

    selected = _select_prompt_files(all_files, select_spec)

    # Apply max_prompts only when selection wasn't an explicit list
    apply_limit = (not select_spec) or (select_spec.strip().lower() in ("", "all"))
    if apply_limit and max_prompts:
        selected = selected[:max_prompts]

    prompts: list[str] = []
    names: list[str] = []
    for p in selected:
        txt = p.read_text(encoding="utf-8").strip()
        if txt:
            prompts.append(txt)
            names.append(p.name)

    return prompts, names
