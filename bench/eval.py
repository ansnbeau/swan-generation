from __future__ import annotations
from collections import Counter
from .utils import normalize_text, tokenize_simple

def levenshtein(a: str, b: str) -> int:
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            tmp = dp[j]
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[j] = min(dp[j] + 1, dp[j-1] + 1, prev + cost)
            prev = tmp
    return dp[lb]

def edit_sim(pred: str, ref: str) -> float:
    if not pred and not ref: return 1.0
    d = levenshtein(pred, ref)
    m = max(len(pred), len(ref), 1)
    return 1.0 - d / m

def token_f1(pred: str, ref: str) -> float:
    p = tokenize_simple(pred); r = tokenize_simple(ref)
    if not p and not r: return 1.0
    if not p or not r: return 0.0
    cp, cr = Counter(p), Counter(r)
    inter = sum((cp & cr).values())
    prec = inter / max(1, sum(cp.values()))
    rec  = inter / max(1, sum(cr.values()))
    return 0.0 if (prec + rec) == 0 else 2 * prec * rec / (prec + rec)

def eval_nl2swan(pred: str, ref: str):
    return {
        "exact": float(normalize_text(pred) == normalize_text(ref)),
        "token_f1": token_f1(pred, ref),
        "edit_sim": edit_sim(pred, ref),
    }

def eval_inline(pred_line: str, ref_line: str):
    return {
        "exact": float(normalize_text(pred_line) == normalize_text(ref_line)),
        "edit_sim": edit_sim(pred_line, ref_line),
    }
