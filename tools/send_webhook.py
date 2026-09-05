# -*- coding: utf-8 -*-
"""Send Short metadata to the sokt.io webhook (n8n workflow trigger).

Reads pick.txt (KEY, NAME, START, END) and the built build/video.mp4,
computes the raw GitHub mp3 link, title, description, tags,
and POSTs a JSON payload to the configured webhook URL.

The video MP4 is uploaded to a GitHub Release ("latest-short") so the
downstream n8n workflow can download it for YouTube upload.

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

    # Short name (title) — NO ayah range to avoid encoding issues
    reciter = "عمار الخطيب"
    short_name = f"🎧 سورة {name} | تلاوة {reciter}"

    # Short description — ayah range stays here (full context for YouTube)
    if start == end:
        ayah_label = f"الآية {start}"
    else:
        ayah_label = f"من الآية {start} إلى الآية {end}"

    short_description = (
        f"تلاوة مباركة بصوت القارئ {reciter} ✨\n"
        f"📖 سورة {name} ({key}) — {ayah_label}\n\n"
        f"🔊 استمع للآية مباشرة:\n{raw_url}\n\n"
        f"📚 المكتبة الكاملة (77 سورة مقسّمة آية آية):\n"
        f"https://github.com/AmmarBasha2011/Ammar-Quran-Record\n\n"
        f"🌐 الموقع: https://ammarbasha2011.github.io/Ammar-Quran-Record/\n\n"
        f"🤲 اللهم اجعل القرآن ربيع قلوبنا. شاركه مع من تحب."
    )

    # Short tags — no ayah range in tags either
    short_tags = [
        "قرآن", "تلاوة", "عمار_الخطيب", "اسلام", "Shorts",
        f"سورة_{name}", "قرآن_كريم", "تلاوات",
    ]

    # File size info (if video was built)
    video_size = 0
    video_path = os.path.join("build", "video.mp4")
    video_url = ""
    if os.path.exists(video_path):
        video_size = os.path.getsize(video_path)
        # Upload to GitHub Release and get download URL
        video_url = upload_to_release(video_path, key, start, end)

    payload = {
        "link": raw_url,
        "video_url": video_url,
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


def upload_to_release(video_path, key, start, end):
    """Upload build/video.mp4 to GitHub Release 'latest-short' and return URL.

    Uses `gh release upload --clobber' so the asset is replaced each run.
    Returns the browser_download_url, or empty string on failure.
    """
    import subprocess

    release_tag = "latest-short"
    asset_name = f"short-{key}-{start:03d}-{end:03d}.mp4"

    try:
        # Create release if it doesn't exist (silent if already exists)
        subprocess.run(
            ["gh", "release", "create", release_tag,
             "--title", "Latest Short",
             "--notes", "Auto-generated Short video (overwritten each run)",
             "--latest"],
            capture_output=True, text=True, timeout=30
        )

        # Upload (overwrite existing asset with same name)
        result = subprocess.run(
            ["gh", "release", "upload", release_tag, video_path,
             "--clobber", "--name", asset_name],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            print(f"Release upload warning: {result.stderr[:200]}")
            return ""

        # Get the download URL
        result = subprocess.run(
            ["gh", "release", "view", release_tag, "--json", "assets"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            assets = json.loads(result.stdout).get("assets", [])
            for asset in assets:
                if asset.get("name") == asset_name:
                    url = asset.get("url", "")
                    print(f"Video uploaded: {url}")
                    return url

        return ""

    except Exception as e:
        print(f"Release upload failed: {e}")
        return ""


if __name__ == "__main__":
    main()
