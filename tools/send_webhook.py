# -*- coding: utf-8 -*-
"""Send Short metadata to the sokt.io webhook (n8n workflow trigger).

Reads pick.txt (KEY, NAME, START, END) and the built build/video.mp4,
computes the raw GitHub mp3 link, title, description, tags,
and POSTs a JSON payload to the configured webhook URL.

Usage (run from repo root):
  python tools/send_webhook.py [webhook_url]
If no argument, uses env SOKT_WEBHOOK_URL.
"""
import os
import sys
import json
import urllib.request


def main():
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "SOKT_WEBHOOK_URL", "https://flow.sokt.io/func/scri445wtgHf"
    )

    # Read pick data
    with open("pick.txt", encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    key, name, start, end = lines[0], lines[1], lines[2], lines[3]

    # Raw mp3 link (first ayah)
    raw_url = (
        f"https://raw.githubusercontent.com"
        f"/AmmarBasha2011/Ammar-Quran-Record/main/{key}/{int(start):03d}.mp3"
    )

    # Ayah label
    if start == end:
        ayah_label = f"الآية {start}"
    else:
        ayah_label = f"الآيات {start}–{end}"

    # Short name (title)
    short_name = f"🎧 سورة {name} | {ayah_label} | تلاوة عمار الخطيب"

    # Short description
    reciter = "عمار الخطيب"
    short_description = (
        f"تلاوة مباركة بصوت القارئ {reciter} ✨\n"
        f"📖 سورة {name} ({key}) — {ayah_label}\n\n"
        f"🔊 استمع للآية مباشرة:\n{raw_url}\n\n"
        f"📚 المكتبة الكاملة (77 سورة مقسّمة آية آية):\n"
        f"https://github.com/AmmarBasha2011/Ammar-Quran-Record\n\n"
        f"🌐 الموقع: https://ammarbasha2011.github.io/Ammar-Quran-Record/\n\n"
        f"🤲 اللهم اجعل القرآن ربيع قلوبنا. شاركه مع من تحب."
    )

    # Short tags
    short_tags = [
        "قرآن", "تلاوة", "عمار_الخطيب", "اسلام", "Shorts",
        f"سورة_{name}", "قرآن_كريم", "تلاوات",
        ayah_label.replace("–", "_").replace(" ", "_"),
    ]

    # File size info (if video was built)
    video_size = 0
    video_path = os.path.join("build", "video.mp4")
    if os.path.exists(video_path):
        video_size = os.path.getsize(video_path)

    payload = {
        "link": raw_url,
        "name": short_name,
        "description": short_description,
        "tags": short_tags,
        "surah_key": key,
        "surah_name": name,
        "ayah_start": int(start),
        "ayah_end": int(end),
        "ayah_label": ayah_label,
        "reciter": reciter,
        "video_size_bytes": video_size,
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    print(f"Sending webhook payload to {webhook_url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.status
        body = resp.read().decode("utf-8", errors="replace")
        print(f"Webhook response: HTTP {status}")
        print(body[:500])

    if status >= 400:
        print(f"ERROR: webhook returned {status}")
        sys.exit(1)

    print("Webhook delivered ✓")


if __name__ == "__main__":
    main()
