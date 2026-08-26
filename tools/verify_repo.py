# -*- coding: utf-8 -*-
"""
verify_repo.py — Independent STT audit of all published ayah files.

Uses tarteel-ai/whisper-base-ar-quran (a DIFFERENT model than the one that
did the splitting) to transcribe every mp3 in the repo, compares against
the official ayah text, and writes a verdict report.

Verdicts:
  OK      sim >= 0.80
  CHECK   0.60 <= sim < 0.80   (worth listening)
  BAD     sim < 0.60           (must listen)
"""
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from arabic_norm import normalize, similarity_ratio

REPO = os.path.join(BASE, "repo")
OUT = os.path.join(BASE, "work", "audit_report.json")
MODELS_DIR = os.path.join(BASE, "models")
MODEL = os.path.join(MODELS_DIR, "whisper-base-ar-quran-ct2")  # CPU int8


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=8)

    idx = json.load(open(os.path.join(HERE, "quran_norm_index.json"),
                         encoding="utf-8"))
    tasks = []
    for folder in sorted(os.listdir(REPO)):
        if not folder.isdigit():
            continue
        key = f"{int(folder):03d}"
        if key not in idx:
            continue
        texts = idx[key]["texts"]
        d = os.path.join(REPO, folder)
        for f in sorted(os.listdir(d)):
            if f.endswith(".mp3") and f[:-4].isdigit():
                ayah = int(f[:-4])
                if 1 <= ayah <= len(texts):
                    tasks.append((key, ayah, os.path.join(d, f), texts[ayah - 1]))

    print(f"auditing {len(tasks)} files...")
    results = []
    t0 = time.time()
    for i, (key, ayah, path, truth) in enumerate(tasks):
        segments, _ = model.transcribe(path, language="ar", beam_size=5)
        hyp = " ".join(s.text.strip() for s in segments)
        sim = round(similarity_ratio(hyp, truth), 3)
        verdict = "OK" if sim >= 0.80 else ("CHECK" if sim >= 0.60 else "BAD")
        results.append({
            "surah": key, "ayah": ayah, "file": path.replace(REPO, "")[1:],
            "sim": sim, "verdict": verdict,
            "heard": normalize(hyp)[:160],
            "expected": truth[:160],
        })
        done = i + 1
        if done % 10 == 0 or done == len(tasks):
            print(f"  {done}/{len(tasks)} ({time.time()-t0:.0f}s)")

    json.dump(results, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # summary
    ok = sum(1 for r in results if r["verdict"] == "OK")
    chk = sum(1 for r in results if r["verdict"] == "CHECK")
    bad = sum(1 for r in results if r["verdict"] == "BAD")
    print(f"\nDONE in {time.time()-t0:.0f}s → {OUT}")
    print(f"OK: {ok} | CHECK: {chk} | BAD: {bad}")
    for r in results:
        if r["verdict"] != "OK":
            print(f'  [{r["verdict"]:5}] {r["surah"]}/{r["ayah"]:03d} sim={r["sim"]}')


if __name__ == "__main__":
    main()
