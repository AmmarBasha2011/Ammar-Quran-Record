# -*- coding: utf-8 -*-
"""Re-cut specific ayahs of an already-split surah using known-correct absolute
boundaries (seconds). Fixes mis-aligned cuts without re-running full ASR.

Find correct boundaries with a word-timestamp diagnostic (see how 035/011 was
fixed: ayah 11 had its opening words stolen by ayah 10 and its tail bled into
ayah 12).

Usage:
  python tools/recut_ayahs.py <surah> <src_audio> <outdir> \
        --bounds 10=290.8:327.4 11=327.4:376.1 12=380.7:447.77

Each bound "A=START:END" re-exports outdir/0AA.mp3 from START..END seconds of
the source, snapped to the nearest silence gap, recomputes similarity, and
updates outdir/_report.json (start/end/sim + weak list).
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quran_split import (load_surah, detect_gaps, snap_to_gap,
                         align_dp)  # noqa
from arabic_norm import window_score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surah", type=int)
    ap.add_argument("src")
    ap.add_argument("outdir")
    ap.add_argument("--bounds", nargs="+", required=True,
                    help="A=START:END per ayah, e.g. 11=327.4:376.1")
    args = ap.parse_args()

    key, meta = load_surah(args.surah)
    bounds = {}
    for b in args.bounds:
        a, rng = b.split("=")
        s, e = rng.split(":")
        bounds[int(a)] = (float(s), float(e))

    from pydub import AudioSegment
    seg = AudioSegment.from_file(args.src)
    gaps = detect_gaps(os.path.abspath(args.src))
    pad = 0.08

    db = json.load(open(os.path.join(args.outdir, "_report.json"),
                        encoding="utf-8"))
    item_by = {it["ayah"]: it for it in db["items"]}

    for a, (s, e) in bounds.items():
        rs = snap_to_gap(s - pad, gaps, tol=0.7)
        rs = rs if abs(rs - (s - pad)) <= 0.7 else max(0.0, s - pad)
        re_ = snap_to_gap(e + pad, gaps, tol=0.7)
        re_ = re_ if abs(re_ - (e + pad)) <= 0.7 else e + pad
        ms0 = int(rs * 1000)
        ms1 = int(min(len(seg), re_ * 1000))
        out = os.path.join(args.outdir, f"{a:03d}.mp3")
        seg[ms0:ms1].export(out, format="mp3", bitrate="128k")

        sim = round(window_score(
            [w for w in meta["texts"][a - 1].split()],
            meta["texts"][a - 1].split()), 3) if False else None
        # proper sim: re-transcribe the clip and compare
        from faster_whisper import WhisperModel
        import tempfile, subprocess
        clip = seg[ms0:ms1]
        ct = os.path.join(args.outdir, f"_rc_{a:03d}.mp3")
        clip.export(ct, format="mp3", bitrate="128k")
        m = WhisperModel(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "models", "whisper-small-ct2"),
            device="cpu", compute_type="int8", cpu_threads=8)
        txt = " ".join(seg_.text for seg_ in m.transcribe(ct, language="ar",
                       beam_size=5, word_timestamps=False)[0])
        from arabic_norm import normalize
        hyp = [normalize(w) for w in txt.split() if normalize(w)]
        sim = round(window_score(hyp, meta["texts"][a - 1]), 3)
        os.remove(ct)

        if a in item_by:
            item_by[a]["start"] = round(ms0 / 1000, 2)
            item_by[a]["end"] = round(ms1 / 1000, 2)
            item_by[a]["sim"] = sim
        print(f"re-cut {a:03d}.mp3 -> {ms0/1000:.2f}-{ms1/1000:.2f}s "
              f"sim={sim}")

    db["items"] = [item_by[i] for i in sorted(item_by)]
    db["weak"] = sorted(it["ayah"] for it in db["items"] if it["sim"] < 0.75)
    json.dump(db, open(os.path.join(args.outdir, "_report.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
    print("updated _report.json, weak:", db["weak"])


if __name__ == "__main__":
    main()
