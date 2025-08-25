import re
from pathlib import Path

def normalize_text(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines()).strip()

def tokenize_simple(s: str):
    return re.findall(r"\w+|[^\w\s]", s, re.UNICODE)

def extract_code_block(text: str, lang_hint: str | None = None) -> str:
    if not text:
        return ""
    pattern = r"```([a-zA-Z0-9_+.\-]*)\n(.*?)```"
    matches = re.findall(pattern, text, flags=re.DOTALL)
    if not matches:
        return text.strip()
    if lang_hint:
        for lang, code in matches:
            if (lang or "").lower() == lang_hint.lower():
                return code.strip()
    return matches[0][1].strip()

def first_nonempty_line(text: str, lang_hint: str | None = None) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if "```" in t:
        t = extract_code_block(t, lang_hint or "")
    for line in t.splitlines():
        ln = line.strip()
        if ln:
            return ln
    return ""

def timestamped_run_dir(base: Path, slug: str) -> Path:
    from datetime import datetime
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", slug.strip())[:120].strip("-")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = base / f"{ts}__{safe}"
    out.mkdir(parents=True, exist_ok=True)
    return out
