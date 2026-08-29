# -*- coding: utf-8 -*-
"""Read channel + video statistics from YouTube and compare Shorts vs Long-form.

Reads YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN from env (same as upload).
Prints a comparison so we can see if our auto-Shorts outperform other videos.

Usage:
  python tools/youtube_stats.py
"""
import os
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


def main():
    yt = get_service()

    # 1) channel stats
    ch = yt.channels().list(part="statistics,snippet", mine=True).execute()
    ch0 = ch["items"][0]
    stats = ch0["statistics"]
    print("=== CHANNEL ===")
    print("title      :", ch0["snippet"]["title"])
    print("subscribers:", stats.get("subscriberCount"))
    print("total views:", stats.get("viewCount"))
    print("video count:", stats.get("videoCount"))
    print()

    # 2) list all videos (newest first), grab stats + duration
    videos = []
    next_page = None
    while True:
        resp = yt.playlistItems().list(
            part="contentDetails",
            playlistId=ch0["contentDetails"]["relatedPlaylists"]["uploads"],
            maxResults=50,
            pageToken=next_page,
        ).execute()
        ids = [i["contentDetails"]["videoId"] for i in resp["items"]]
        if ids:
            det = yt.videos().list(
                part="statistics,snippet,contentDetails",
                id=",".join(ids),
            ).execute()
            for v in det["items"]:
                dur = v["contentDetails"]["duration"]  # PT#M#S
                mins = parse_duration(dur)
                is_short = (mins < 3)  # YouTube classifies <=3min vertical as Short
                views = int(v["statistics"].get("viewCount", 0))
                likes = int(v["statistics"].get("likeCount", 0))
                videos.append({
                    "id": v["id"],
                    "title": v["snippet"]["title"],
                    "mins": mins,
                    "is_short": is_short,
                    "views": views,
                    "likes": likes,
                })
        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    shorts = [v for v in videos if v["is_short"]]
    longs = [v for v in videos if not v["is_short"]]

    print(f"=== COMPARISON ({len(videos)} videos) ===")
    print(f"Shorts: {len(shorts)} | Long-form: {len(longs)}")
    print()

    def avg(lst, key):
        return sum(x[key] for x in lst) / len(lst) if lst else 0

    print(f"Shorts   avg views: {avg(shorts,'views'):.0f} | avg likes: {avg(shorts,'likes'):.0f}")
    print(f"Long-form avg views: {avg(longs,'views'):.0f} | avg likes: {avg(longs,'likes'):.0f}")
    print()

    print("=== TOP 5 SHORTS ===")
    for v in sorted(shorts, key=lambda x: -x["views"])[:5]:
        print(f"  {v['views']:>7} views | {v['title'][:50]}")
    print()
    print("=== TOP 5 LONG-FORM ===")
    for v in sorted(longs, key=lambda x: -x["views"])[:5]:
        print(f"  {v['views']:>7} views | {v['title'][:50]}")


def parse_duration(dur):
    # PT#M#S -> minutes (float)
    import re
    m = re.findall(r"(\d+)([HMS])", dur)
    total = 0.0
    for val, unit in m:
        val = int(val)
        if unit == "H":
            total += val * 60
        elif unit == "M":
            total += val
        elif unit == "S":
            total += val / 60.0
    return total


if __name__ == "__main__":
    main()
