# -*- coding: utf-8 -*-
"""
Add a freshly-cut surah to the repo, preserving _report.json (quality metrics).

Usage:  python add_surah.py 036
  -> copies cut_one/036/0*.mp3  +  cut_one/036/_report.json  into  repo/036/
  -> does NOT copy *_source.mp3
"""
import os, sys, json, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "repo")

def main():
    if len(sys.argv) < 2:
        print("usage: python add_surah.py <surah3>")
        sys.exit(1)
    key = sys.argv[1]
    src = os.path.join(BASE, "cut_one", key)
    dst = os.path.join(REPO, key)
    if not os.path.isdir(src):
        print(f"no cut dir: {src}")
        sys.exit(1)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(src)):
        if f.endswith(".mp3") and f[:3].isdigit() and len(f) == 7:
            shutil.copy(os.path.join(src, f), os.path.join(dst, f)); n += 1
        if f == "_report.json":
            shutil.copy(os.path.join(src, f), os.path.join(dst, f))
    # rebuild available.json (now includes metrics)
    subprocess = __import__("subprocess")
    subprocess.run([sys.executable, os.path.join(BASE, "rebuild_available.py")], check=False)
    print(f"added {n} ayah mp3s (+_report.json) for surah {key}")

if __name__ == "__main__":
    main()
