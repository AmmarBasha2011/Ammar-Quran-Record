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

    title = f"سورة {name} ({key}) - الآية {start}" + (f"-{end}" if end != start else "")
    desc = (
        f"تلاوة عمار الخطيب\n"
        f"سورة {name} ({key}) الآيات {start}-{end}\n"
        f"#Shorts #قرآن #تلاوة"
    )
    tags = ["قرآن", "تلاوة", "عمار_الخطيب", "اسلام", "Shorts"]

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
