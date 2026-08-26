# -*- coding: utf-8 -*-
"""
process_parallel.py — FULL parallel pipeline for multiple surahs.

For each (url, surah_number) given on the command line:
  1. download audio (yt-dlp)            [sequential is fine, fast]
  2. split into per-ayah mp3           [one Process per surah -> uses all cores]
  3. INDEPENDENT STT audit (whisper-base-ar-quran, a DIFFERENT model)
     on every produced file             [ParallelProcessPool over all files]
  4. any BAD/CHECK file -> flagged for manual review (no auto-publish)

This is the "Full (2)" mode: same per-surah quality, but the WHOLE batch
runs in parallel across the 16 logical CPUs, and every file is independently
verified before publish.

Usage:
  python tools/process_parallel.py \
      "https://youtu.be/XXXX" 1 \
      "https://youtu.be/YYYY" 2 \
      ...
"""
import os, sys, json, time, subprocess, argparse
from multiprocessing import Process, Pool, cpu_count

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
WORK = os.path.join(BASE, "work")
REPO = os.path.join(BASE, "repo")
TOOLS = os.path.join(BASE, "tools")
SPLIT = os.path.join(TOOLS, "quran_split.py")
AUDIT_MODEL = os.path.join(BASE, "models", "whisper-base-ar-quran-ct2")
IDX = json.load(open(os.path.join(TOOLS, "quran_norm_index.json"), encoding="utf-8"))


# ---------------------------------------------------------------------------
# Step 1: download
# ---------------------------------------------------------------------------
def download(url):
    out_tmpl = os.path.join(WORK, "yt_%(id)s.%(ext)s")
    r = subprocess.run(
        ["yt-dlp", "-f", "bestaudio[abr<=128]/bestaudio", "-x",
         "--audio-format", "mp3", "--audio-quality", "128K",
         "-o", out_tmpl, url],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        raise RuntimeError(f"download failed: {r.stderr[-300:]}")
    # find the produced file
    vid = url.split("/")[-1].split("?")[0]
    path = os.path.join(WORK, f"yt_{vid}.mp3")
    if not os.path.exists(path):
        # yt-dlp may have kept a different ext; find newest mp3 in WORK
        cands = sorted([f for f in os.listdir(WORK) if f.startswith("yt_") and f.endswith(".mp3")],
                       key=lambda f: os.path.getmtime(os.path.join(WORK, f)))
        path = os.path.join(WORK, cands[-1])
    return path


# ---------------------------------------------------------------------------
# Step 2: split one surah in its own process
# ---------------------------------------------------------------------------
def split_one(args):
    url, surah = args
    vid = url.split("/")[-1].split("?")[0]
    audio = os.path.join(WORK, f"yt_{vid}.mp3")
    if not os.path.exists(audio):
        audio = download(url)
    out = os.path.join(WORK, f"out_{surah:03d}")
    os.makedirs(out, exist_ok=True)
    r = subprocess.run(
        [sys.executable, SPLIT, audio, str(surah), out],
        capture_output=True, text=True, timeout=1800,
    )
    # count produced files
    n = len([f for f in os.listdir(out) if f.endswith(".mp3")])
    return surah, n, r.returncode, (r.stderr[-200:] if r.returncode else "")


# ---------------------------------------------------------------------------
# Step 3: independent audit on a single file (worker)
# ---------------------------------------------------------------------------
def audit_one(task):
    from faster_whisper import WhisperModel
    from arabic_norm import normalize, similarity_ratio
    surah, ayah, path, truth = task
    # lazily create one model per worker process
    if not hasattr(audit_one, "model"):
        audit_one.model = WhisperModel(
            AUDIT_MODEL, device="cpu", compute_type="int8", cpu_threads=2)
    segs, _ = audit_one.model.transcribe(path, language="ar", beam_size=5)
    hyp = " ".join(s.text.strip() for s in segs)
    sim = round(similarity_ratio(hyp, truth), 3)
    verdict = "OK" if sim >= 0.80 else ("CHECK" if sim >= 0.60 else "BAD")
    return {
        "surah": f"{surah:03d}", "ayah": ayah,
        "file": path.replace(REPO, "")[1:],
        "sim": sim, "verdict": verdict,
        "heard": normalize(hyp)[:160], "expected": truth[:160],
    }


def collect_audit_tasks(surahs):
    tasks = []
    for surah in surahs:
        key = f"{surah:03d}"
        out = os.path.join(WORK, f"out_{key}")
        texts = IDX[key]["texts"]
        for f in sorted(os.listdir(out)):
            if f.endswith(".mp3") and f[:-4].isdigit():
                ayah = int(f[:-4])
                if 1 <= ayah <= len(texts):
                    tasks.append((surah, ayah, os.path.join(out, f), texts[ayah - 1]))
    return tasks


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+",
                    help="pairs of URL SURAH_NUMBER, e.g. URL 1 URL 2 ...")
    args = ap.parse_args()
    pairs = []
    i = 0
    while i < len(args.items):
        pairs.append((args.items[i], int(args.items[i + 1])))
        i += 2
    surahs = [s for _, s in pairs]
    print(f"FULL-PARALLEL pipeline: {len(pairs)} surahs -> {surahs}")

    t0 = time.time()
    # Step 1+2: split each surah in its own Process
    nproc = min(len(pairs), max(1, cpu_count() // 2))
    print(f"[1/3] downloading + splitting {len(pairs)} surahs on {nproc} processes...")
    with Pool(nproc) as p:
        split_results = p.map(split_one, pairs)
    for surah, n, rc, err in split_results:
        status = "OK" if rc == 0 else f"FAIL({err})"
        print(f"   surah {surah:03d}: {n} files {status}")

    # Step 3: independent audit (full) over every produced file, parallel
    tasks = collect_audit_tasks(surahs)
    print(f"[2/3] independent STT audit of {len(tasks)} files (parallel)...")
    with Pool(min(cpu_count(), 8)) as p:
        results = p.map(audit_one, tasks)
    json.dump(results, open(os.path.join(WORK, "audit_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    ok = sum(1 for r in results if r["verdict"] == "OK")
    chk = sum(1 for r in results if r["verdict"] == "CHECK")
    bad = sum(1 for r in results if r["verdict"] == "BAD")
    print(f"[3/3] audit done in {time.time()-t0:.0f}s | OK:{ok} CHECK:{chk} BAD:{bad}")
    for r in results:
        if r["verdict"] != "OK":
            print(f'   [{r["verdict"]:5}] {r["surah"]}/{r["ayah"]:03d} sim={r["sim"]}')

    # flag for manual review
    flagged = [(r["surah"], r["ayah"], r["verdict"]) for r in results if r["verdict"] != "OK"]
    json.dump({"flagged": flagged, "summary": {"ok": ok, "check": chk, "bad": bad}},
              open(os.path.join(WORK, "audit_flags.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("Flagged files written to work/audit_flags.json -> publish only after review.")


if __name__ == "__main__":
    main()
