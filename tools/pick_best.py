# -*- coding: utf-8 -*-
"""Pick a previously-uploaded high-performing Short to re-upload.

Strategy: query the channel's uploads, find the top videos by viewCount
that are Shorts (< 3 min), and pick one at random from the top-N.
Then output its source surah/ayah so video-reupload.yml can rebuild + re-post it.

Writes pick.txt (KEY, NAME, START, END) compatible with upload_youtube.py.

Usage (CI):  python tools/pick_best.py
"""
import os
import json
import random
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/youtube.upload"]


def get_service():
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def parse_duration(dur):
    import re
    mins = 0.0
    for val, unit in re.findall(r"(\d+)([HMS])", dur):
        val = int(val)
        if unit == "H":
            mins += val * 60
        elif unit == "M":
            mins += val
        elif unit == "S":
            mins += val / 60.0
    return mins


def main():
    yt = get_service()
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # collect all uploads (up to 200 most recent)
    videos = []
    page = None
    while len(videos) < 200:
        resp = yt.playlistItems().list(
            part="contentDetails", playlistId=uploads,
            maxResults=50, pageToken=page).execute()
        ids = [i["contentDetails"]["videoId"] for i in resp["items"]]
        if ids:
            det = yt.videos().list(
                part="statistics,snippet,contentDetails", id=",".join(ids)).execute()
            for v in det["items"]:
                mins = parse_duration(v["contentDetails"]["duration"])
                if mins < 3:  # Short only
                    title = v["snippet"]["title"]
                    # try to parse "سورة X (KEY) - الآية A-B" from our titles
                    import re
                    m = re.search(r"سورة .*?\((\d{3})\)\s*-\s*الآية (\d+)(?:-(\d+))?", title)
                    if m:
                        key, start = m.group(1), int(m.group(2))
                        end = int(m.group(3)) if m.group(3) else start
                        videos.append({
                            "id": v["id"], "key": key, "start": start, "end": end,
                            "views": int(v["statistics"].get("viewCount", 0)),
                            "title": title,
                        })
        page = resp.get("nextPageToken")
        if not page:
            break

    if not videos:
        print("No past Shorts found to re-upload.")
        # fallback: write a dummy so workflow can skip
        open("pick.txt", "w").write("")
        return

    # top 10 by views, pick one at random
    top = sorted(videos, key=lambda x: -x["views"])[:10]
    pick = random.choice(top)
    with open("pick.txt", "w") as f:
        f.write(f"{pick['key']}\n{pick['key']}\n{pick['start']}\n{pick['end']}\n")
    print(f"re-upload pick: surah {pick['key']} ayahs {pick['start']}-{pick['end']} "
          f"({pick['views']} views originally)")


if __name__ == "__main__":
    main()
