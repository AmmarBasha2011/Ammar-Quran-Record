# -*- coding: utf-8 -*-
"""
quran_split.py — Split a full-surah recording into per-ayah MP3 files.

Pipeline:
  1. faster-whisper (tarteel quran model, CT2 int8) transcribes with timestamps
  2. word-level timeline is aligned against the official ayah texts
     using normalized Arabic + SequenceMatcher sliding window
  3. audio is cut at each ayah boundary -> surah_folder/NNN.mp3
  4. verification report: count match + text similarity per ayah

Usage:
  python quran_split.py <audio_file> <surah_number> <out_dir> [--beam N]

Author: prepared for Ammar's Quran archive (AmmarBasha2011/Ammar-Quran-Record)
"""
import sys, os, json, time, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arabic_norm import normalize, similarity_ratio

# Paths are resolved relative to this script so the tool works on any machine.
TOOLS = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(TOOLS), "models")
MODEL_CT2 = os.path.join(MODELS_DIR, "whisper-small-ct2")                # CPU int8 — best Arabic accuracy
MODEL_FP16 = os.path.join(MODELS_DIR, "whisper-base-ar-quran-ct2-fp16")  # GPU float16 (fast but less accurate)


def load_surah(num: int):
    idx = json.load(open(f"{TOOLS}/quran_norm_index.json", encoding="utf-8"))
    key = f"{num:03d}"
    return key, idx[key]


def _setup_cuda():
    """Expose pip-provided CUDA libs so ctranslate2 can load them (Windows)."""
    import os, sysconfig
    sp = sysconfig.get_paths()["purelib"]
    dirs = []
    for sub in ("cublas", "cudnn", "cuda_nvrtc"):
        p = os.path.join(sp, "nvidia", sub, "bin")
        if os.path.isdir(p):
            os.add_dll_directory(p)
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
            dirs.append(p)
    return bool(dirs)


def transcribe(audio: str, beam: int = 5):
    from faster_whisper import WhisperModel

    def _run(model):
        segments, info = model.transcribe(audio, language="ar", beam_size=beam,
                                          vad_filter=False, word_timestamps=True)
        words = []          # (start, end, word)
        ok = True
        try:
            for seg in segments:
                if not seg.words:
                    continue
                for w in seg.words:
                    t = normalize(w.word)
                    if t and not t.isdigit():   # drop timestamp hallucinations ('7')
                        words.append((w.start, w.end, t))
        except RuntimeError as e:
            if ".dll" in str(e).lower() or "cublas" in str(e).lower():
                ok = False
            else:
                raise
        return words, ok

    # CPU int8 + beam5 produces the cleanest Arabic for the tarteel quran model;
    # GPU fp16 runs ~20x faster but mangles words badly on this card, which breaks
    # alignment. Strategy: CPU primary (13x realtime is plenty), GPU only when the
    # user explicitly forces it via --gpu.
    import os, sysconfig
    sp = sysconfig.get_paths()["purelib"]
    for sub in ("cublas", "cudnn", "cuda_nvrtc"):
        p = os.path.join(sp, "nvidia", sub, "bin")
        if os.path.isdir(p):
            os.add_dll_directory(p)

    if os.environ.get("QURAN_GPU") == "1":
        try:
            mgpu = WhisperModel(MODEL_FP16, device="cuda", compute_type="float16")
            words, ok = _run(mgpu)
            if ok and len(words) > 0:
                print("[asr device: cuda (forced)]")
                return words
        except Exception:
            pass

    model = WhisperModel(MODEL_CT2, device="cpu", compute_type="int8",
                         cpu_threads=8)
    words, ok = _run(model)
    print("[asr device: cpu beam5]")
    return words


INTRO_WORDS = {"بسم", "باسم", "الله", "الرحمن", "الرحيم",
               "اعوذ", "أعوذ", "بالله", "من", "الشيطان", "الرجيم",
               "وحنان", "وحيم", "حنان", "رحمان", "رحمن", "رحيم"}


def find_best_start(words, ayah_texts, max_scan=16):
    """The recording often opens with isti3adha + basmala. ASR mangles both the
    intro AND possibly the first ayah's opening words (e.g. 'قل أعوذ' heard as
    'كل عمل'), so a pure max-score scan can SKIP real ayah words and destroy
    ayah 1. Two-phase strategy:
      1. scan all starts, keep the highest-total alignment
      2. walk BACKWARD from that start while: the previous word is not basmala
         vocabulary, and total score stays within tolerance — this re-includes
         genuine ayah-opening words that scoring alone dropped."""
    scored = []
    # scan far enough to cover a long basmala: up to half the words,
    # but never exclude the boundary case (W//2 itself)
    # ONE align_dp pass. The old code re-ran this up to 'max_scan' times (a full
    # forward scan for the best opening), which turned a 75s alignment into ~20 min
    # for a 20-ayah surah. We skip the opening isti3adha+basmala cheaply: scan
    # forward a bounded number of words and start align at the first word that is
    # NOT intro vocabulary. This is O(scan) and costs no re-alignment.
    start = 0
    for j in range(min(max_scan, len(words))):
        if normalize(words[j][2]) not in INTRO_WORDS:
            start = j
            break
    res, comp = align_dp(words[start:], ayah_texts)
    if len(res) != len(ayah_texts):
        return res if res else None
    return res



_WINDOW_CACHE = {}
def _window_score_cached(a_idx, w0, w1, ayah_texts, words):
    from arabic_norm import window_score
    key = (a_idx, w0, w1)
    if key in _WINDOW_CACHE:
        return _WINDOW_CACHE[key]
    hyp = [w[2] for w in words[w0:w1]]
    s = window_score(hyp, ayah_texts[a_idx])
    _WINDOW_CACHE[key] = s
    return s

def _reset_window_cache():
    _WINDOW_CACHE.clear()

def align_dp(words, ayah_texts):
    """Global optimal alignment via DP over cut points.
    dp[i][a] = best total score having consumed i words and a ayahs.
    Window length for ayah a is constrained to ±60% around its expected
    word count (with slack), keeping this fast even for Al-Baqara."""
    from arabic_norm import window_score
    n = len(ayah_texts)
    W = len(words)

    NEG = float("-inf")
    # dp[(i, a)] = (best_total_score, k_chosen) ; reconstruct at the end
    dp = {(0, 0): (0.0, 0)}
    parent = {}

    _reset_window_cache()
    for a in range(n):
        elen = max(1, len(ayah_texts[a].split()))
        lo_k = max(1, int(elen * 0.4))
        hi_k = max(int(elen * 2.5), elen + 8)
        for i in range(W + 1):
            if (i, a) not in dp:
                continue
            score_so_far, _ = dp[(i, a)]
            for k in range(lo_k, min(hi_k, W - i) + 1):
                s = _window_score_cached(a, i, i + k, ayah_texts, words)
                total = score_so_far + s
                key = (i + k, a + 1)
                if key not in dp or total > dp[key][0]:
                    dp[key] = (total, k)
                    parent[key] = (i, a, k)

    # finish: prefer consuming MORE words on near-ties — trailing words almost
    # always belong to the last ayah (only true outro noise is left otherwise)
    best_i, best_s = None, float("-inf")
    for i in range(W, -1, -1):
        if (i, n) in dp:
            adj = dp[(i, n)][0] + 0.08 * i
            if adj > best_s:
                best_s, best_i = adj, i

    # backtrack
    cuts = []
    cur = (best_i, n)
    while cur in parent:
        pi, pa, k = parent[cur]
        cuts.append((pi, pi + k))
        cur = (pi, pa)
    cuts.reverse()

    result = []
    for ai, (w0, w1) in enumerate(cuts):
        hyp = [w[2] for w in words[w0:w1]]
        result.append({"ayah": ai + 1, "w0": w0, "w1": w1,
                       "sim": round(window_score(hyp, ayah_texts[ai]), 3),
                       "t_start": words[w0][0],
                       "t_end": words[w1 - 1][1]})
    complete = len(result) == n
    return result, complete


def detect_gaps(audio_path, noise=-30, min_d=0.12):
    """Return list of (gap_start, gap_end) silences via ffmpeg silencedetect."""
    import subprocess, re as _re
    r = subprocess.run(["ffmpeg", "-i", audio_path,
                        "-af", f"silencedetect=noise={noise}dB:d={min_d}",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=180)
    starts = [float(m) for m in _re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(m) for m in _re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def snap_to_gap(t_sec, gaps, tol=0.7):
    """If a silence gap lies within tol of t_sec, return its midpoint (a natural
    speech boundary); otherwise return t_sec unchanged."""
    best = None
    for gs, ge in gaps:
        mid = (gs + ge) / 2
        if abs(mid - t_sec) <= tol and (best is None or abs(mid - t_sec) < abs(best - t_sec)):
            best = mid
    return best if best is not None else t_sec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("surah", type=int)
    ap.add_argument("outdir")
    ap.add_argument("--beam", type=int, default=5)
    args = ap.parse_args()

    key, meta = load_surah(args.surah)
    print(f"Surah {key} — {meta['name']} — {meta['ayahs']} ayahs")

    t0 = time.time()
    words = transcribe(args.audio, args.beam)
    t_tr = time.time() - t0
    dur_audio = None
    from pydub import AudioSegment
    seg_all = AudioSegment.from_file(args.audio)
    dur_audio = len(seg_all) / 1000.0
    print(f"transcribed {len(words)} words in {t_tr:.0f}s "
          f"({dur_audio/t_tr:.1f}x realtime)")

    aligned = find_best_start(words, meta["texts"])
    if aligned is None:                     # fallback: assume no intro
        aligned, _ = align_dp(words, meta["texts"])
    leftover = len(words) - (aligned[-1]["w1"] if aligned else 0)
    # completeness = all expected ayahs found; trailing extra words are normal
    # (intro noise / music / basmala) and only warn when substantial
    complete = len(aligned) == meta["ayahs"]
    ok = [a for a in aligned if a["sim"] >= 0.75]
    weak = [a for a in aligned if a["sim"] < 0.75]
    print(f"aligned: {len(aligned)}/{meta['ayahs']} | good:{len(ok)} weak:{len(weak)}"
          f" | trailing words: {leftover}")

    os.makedirs(args.outdir, exist_ok=True)
    from pydub import AudioSegment
    export_db = {
        "surah": key, "name": meta["name"], "source": os.path.abspath(args.audio),
        "ayahs_expected": meta["ayahs"], "ayahs_found": len(aligned),
        "complete": complete, "weak": [a["ayah"] for a in weak], "items": []
    }
    pad = 250  # ms of padding before first cut / after last cut
    gaps = detect_gaps(os.path.abspath(args.audio))

    # 1) compute raw boundary times (seconds) — USE WORD-LEVEL TIMESTAMPS
    #    (forced alignment from faster-whisper) as the primary boundary,
    #    falling back to silencedetect snapping only when a word timestamp
    #    is clearly off (no nearby silence). This fixes truncated/padded cuts
    #    that pure silencedetect produced (e.g. 074/030, 069/001).
    raws = []                        # (raw_start, raw_end) per ayah
    for j, a in enumerate(aligned):
        ts = a["t_start"]            # start of first word in ayah (sec)
        te = a["t_end"]              # end of last word in ayah (sec)
        # primary: word timestamp + small pad; snap to gap only if a silence
        # lies very close (keeps natural breath boundaries when present)
        gap_rs = snap_to_gap(ts - 0.05, gaps, tol=0.25)
        rs = gap_rs if abs(gap_rs - (ts - 0.05)) <= 0.25 else max(0.0, ts - 0.08)
        gap_re = snap_to_gap(te + 0.05, gaps, tol=0.25)
        re_ = gap_re if abs(gap_re - (te + 0.05)) <= 0.25 else te + 0.08
        raws.append((rs, re_))

    # 2) shared boundaries: where consecutive ayahs' word boundaries are very
    #    close (overlap / back-to-back), split at the midpoint instead of
    #    padding — avoids clipping the next ayah's opening word.
    ms_bounds = [int(max(0.0, raws[0][0] - pad / 1000.0) * 1000)]
    for j in range(len(aligned) - 1):
        gap = raws[j][1] - raws[j + 1][0]
        if gap >= 0.05:               # clear space between ayahs
            mid = int(raws[j][1] * 1000)
        else:                         # overlapping -> midpoint
            mid = int((raws[j][1] + raws[j + 1][0]) / 2 * 1000)
        ms_bounds.append(mid)
    ms_ends = ms_bounds[1:] + [min(len(seg_all),
                                   int(raws[-1][1] * 1000) + pad)]

    prev_end = 0
    for j, a in enumerate(aligned):
        ms0 = max(ms_bounds[j], prev_end + 1)
        ms1 = max(min(ms_ends[j], len(seg_all)), ms0 + 500)
        prev_end = ms1
        out = os.path.join(args.outdir, f"{a['ayah']:03d}.mp3")
        seg_all[ms0:ms1].export(out, format="mp3", bitrate="128k")
        export_db["items"].append({
            "ayah": a["ayah"], "file": f"{a['ayah']:03d}.mp3",
            "start": round(ms0/1000, 2), "end": round(ms1/1000, 2),
            "sim": a["sim"]})
    json.dump(export_db, open(os.path.join(args.outdir, "_report.json"),
                              "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"exported {len(aligned)} files -> {args.outdir}")
    if not complete or weak:
        print("ATTENTION: needs review — missing:", complete == False,
              "| weak ayahs:", sorted(a['ayah'] for a in weak)[:20])
    else:
        print("ALL CLEAR ✓")


if __name__ == "__main__":
    main()
