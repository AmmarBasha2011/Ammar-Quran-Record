# -*- coding: utf-8 -*-
"""Upload a vertical short to YouTube directly (no middleman).

Reads YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN from env,
refreshes an access token, and uploads build/video.mp4 as a YouTube Short.

Usage (run from repo root):
  python tools/upload_youtube.py KEY NAME START END
where KEY=024 NAME="النور" START=1 END=2
"""
import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def get_credentials():
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    # force refresh -> access_token valid for ~1h
    import google.auth.transport.requests
    creds.refresh(google.auth.transport.requests.Request())
    return creds


def main():
    key, name, start, end = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    video_file = os.path.join("build", "video.mp4")
    if not os.path.exists(video_file):
        print("ERROR: build/video.mp4 not found")
        sys.exit(1)

    creds = get_credentials()
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=creds)

    reciter = "عمار الخطيب"
    channel = "INEX Team"

    # Build ayah range label
    if start == end:
        ayah_label = f"الآية {start}"
    else:
        ayah_label = f"الآيات {start}–{end}"

    # Title: attractive + keyword-rich (surah name first for search)
    emoji = "🎧"
    if start == end:
        title = f"{emoji} سورة {name} | {ayah_label} | تلاوة {reciter}"
    else:
        title = f"{emoji} سورة {name} | {ayah_label} | تلاوة {reciter}"

    # Long-form (full surah) video — linked as "related" guidance in the Short.
    # NOTE: YouTube Data API v3 has NO endpoint to set a Short's official
    # "Related video". The supported, API-safe way to connect a Short to its
    # long-form video is to surface the long-form URL prominently in the
    # Short's description (and tags), so viewers can tap through. (Adding to a
    # playlist would require the youtube.force-ssl scope, which this token lacks.)
    long_url = ""
    try:
        _links = json.load(open("links.json", encoding="utf-8")).get("links", {})
        long_url = _links.get(key, {}).get("url", "")
    except Exception:
        long_url = ""

    # Description: rich, with direct listening link + the long-form video link
    raw_url = f"https://raw.githubusercontent.com/AmmarBasha2011/Ammar-Quran-Record/main/{key}/{int(start):03d}.mp3"
    desc = (
        f"تلاوة مباركة بصوت القارئ {reciter} ✨\n"
        f"📖 سورة {name} ({key}) — {ayah_label}\n\n"
        f"🔊 استمع للآية مباشرة:\n{raw_url}\n\n"
    )
    if long_url:
        desc += (
            f"🎬 التلاوة الكاملة لسورة {name} (فيديو طويل):\n{long_url}\n\n"
        )
    desc += (
        f"📚 المكتبة الكاملة (76 سورة مقسّمة آية آية):\n"
        f"https://github.com/AmmarBasha2011/Ammar-Quran-Record\n\n"
        f"🌐 الموقع: https://ammarbasha2011.github.io/Ammar-Quran-Record/\n\n"
        f"🤲 اللهم اجعل القرآن ربيع قلوبنا. شاركه مع من تحب.\n\n"
        f"#قرآن #تلاوة #عمار_الخطيب #سورة_{name} "
        f"#{ayah_label.replace('–', '_').replace(' ', '_')} #اسلام #Shorts #قرآن_كريم"
    )
    tags = [
        "قرآن", "تلاوة", "عمار_الخطيب", "اسلام", "Shorts",
        f"سورة_{name}", "قرآن_كريم", "تلاوات",
    ]
    if long_url:
        # surface the long-form id in tags so YouTube can associate the two
        import re as _re
        _m = _re.search(r"v=([A-Za-z0-9_-]{11})", long_url)
        if _m:
            tags.append(f"vid_{_m.group(1)}")


    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True,
                            mimetype="video/mp4")

    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  uploaded {int(status.progress() * 100)}%")
    vid = response["id"]
    print(f"YOUTUBE_VIDEO_ID={vid}")
    print(f"https://youtube.com/shorts/{vid}")


if __name__ == "__main__":
    main()
