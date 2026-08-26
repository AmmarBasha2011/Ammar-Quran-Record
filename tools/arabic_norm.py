# -*- coding: utf-8 -*-
"""Arabic text normalization for Quran text matching (Hafs)."""
import re

TASHKEEL = re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]')  # harakat + quranic marks
TATWEEL = re.compile(r'\u0640')

# letter variants that sound identical in recitation
REPL = {
    'أ':'ا', 'إ':'ا', 'آ':'ا', 'ٱ':'ا', 'ٳ':'ا',
    'ة':'ه',
    'ى':'ي',      # alif maqsura -> ya
    'ؤ':'و', 'ئ':'ي',
}

def normalize(text: str) -> str:
    t = TASHKEEL.sub('', text)
    t = TATWEEL.sub('', t)
    for src, dst in REPL.items():
        t = t.replace(src, dst)
    # unify hamza on seat
    t = re.sub(r'[^\u0621-\u064A0-9 ]', '', t)  # keep arabic letters/digits/space only
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# ---------- single-word fuzzy matching ----------
def word_match(asr_w: str, txt_w: str) -> float:
    """0..1 similarity of one ASR word to one target word.
    Hybrid: structural rules (prefix/containment) + char-level SequenceMatcher.
    The char-level part rescues the tarteel GPU model's scrambled merges
    like يمدين ~ دين or نهادن ~ اهدنا."""
    if asr_w == txt_w:
        return 1.0
    base = 0.0
    if len(asr_w) >= 3 and len(txt_w) >= 3 and \
       asr_w.startswith(txt_w[:3]) and asr_w[1:4] == txt_w[1:4]:
        base = 0.85
    contain = 0.0
    if asr_w and txt_w and (asr_w in txt_w or txt_w in asr_w):
        contain = 0.8 + 0.2 * min(len(asr_w), len(txt_w)) / max(len(asr_w), len(txt_w))
    from difflib import SequenceMatcher
    char_sim = SequenceMatcher(None, asr_w, txt_w).ratio()
    return max(base, contain, char_sim)


def window_score(asr_words, target_text, recall_weight=0.5):
    """Order-preserving alignment score of an ASR word window vs an ayah text.
    Combines precision (how well ASR words match target words) with a weighted
    recall term (did we cover the whole ayah?)."""
    tw = target_text.split()
    n, m = len(asr_words), len(tw)
    if n == 0 or m == 0:
        return 0.0
    used = [False] * m
    total = 0.0
    hits = 0.0
    j = 0
    for a in asr_words:
        best, best_k = 0.0, -1
        for k in range(j, min(m, j + 6)):
            if not used[k]:
                s = word_match(a, tw[k])
                if s > best:
                    best, best_k = s, k
        if best >= 0.5:
            used[best_k] = True
            total += best
            hits += 1
            j = best_k + 1
    precision = total / n
    recall = hits / m
    return (precision + recall_weight * recall) / (1 + recall_weight)


def similarity_ratio(a: str, b: str) -> float:
    """Char-level similarity after normalization (SequenceMatcher).
    Kept for reporting; alignment itself uses window_score."""
    from difflib import SequenceMatcher
    na, nb = normalize(a), normalize(b)
    if not na and not nb: return 1.0
    if not na or not nb: return 0.0
    return SequenceMatcher(None, na, nb).ratio()
