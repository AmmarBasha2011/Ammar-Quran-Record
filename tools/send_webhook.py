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

    # Short name (title) — beautiful, clickable, NO ayah range (encoding)
    reciter = "عمار الخطيب"
    # inspiring title templates (randomly picked each run)
    title_templates = [
        f"🤲 {name} هتساعدك تنام الليلة",
        f"💎 آيات من {name} لو سمعتها هتفهم ليه بنعيش",
        f"🕊️ {name} — لما الدنيا تِضيق بيك",
        f"🌙 سورة {name} بصوت هادي مالوش زي",
        f"🤍 {name} — حاجة جميلة ليومك",
        f"😮 سورة {name} اللي محدش بيسمعها بتركيز",
        f"💛 سورة {name} — خد بريك من اللي بيحصلك",
        f"🫶 {name} بصوت عمار الخطيب",
        f"🌿 سورة {name} — هتروق أي قلبك",
        f"❤️ {name} — استمع قبل ما تفوتك",
        f"✨ سورة {name} — بداية حلوة لليوم",
        f"🕊️ {name} — ساعة القرآن",
        f"💎 {name} — لو بتحب تسمع حلو",
        f"🤲 {name} — عايز تطلع من الدنيا دي؟",
        f"🌙 {name} بصوت هادي — اسمع بقلبك",
        f"😊 {name} — الجمال اللي كنت مستنّيه",
        f"🫶 {name} — اسمع وهتفهم",
        f"💛 {name} — بصوت عمار الخطيب 🎧",
        f"🤍 {name} — رسالتك النهارده",
        f"🌿 {name} — دقيقة من السلام",
        f"🕌 {name} — كلام ربنا ليك",
        f"🤍 سورة {name} — لو عندك هم اسمعها",
        f"🌙 {name} — بصوت هيفكك من كل حاجة",
        f"💛 {name} — تلاوة هتخليك تبكي من الفرحة",
        f"🕊️ {name} — السكينة اللي كنت عايزها",
        f"💎 {name} — اسمع كأنك بتسمعها أول مرة",
        f"🌿 {name} — حضن القرآن ليك",
        f"🤲 {name} — هتحس إن حد معاك",
        f"✨ {name} — خليها في الخلفية واشعر",
        f"❤️ {name} — لو بتحب القرآن اسمع دي",
        f"😊 {name} — أحلى حاجة هتسمعها النهارده",
        f"🫶 {name} — بصوت هيخليك تعيش اللحظة",
        f"💛 {name} — عشان محتاج تطمن",
        f"🌙 {name} — سورة لو سمعتها مش هتنام من الفرحة",
        f"🕊️ {name} — دقيقة بس تفرق كتير",
        f"🤍 {name} — اسمع وفكر في معناها",
        f"💎 {name} — القران بيك",
        f"🤲 {name} — عشان قلبك محتاج يسمع",
        f"🌿 {name} — الجو اللي مالوش زي",
        f"😊 {name} — هتبقى أحسن بعد ما تسمع",
        f"✨ {name} — رسالتك من ربنا دلوقتي",
        f"❤️ {name} — اسمع وقول رأيك",
        f"🫶 {name} — الساعة دي عشان إنت",
        f"💛 {name} — بصوت عمار الخطيب هيفرق معاك",
        f"🌙 {name} — عشان اللي بيحصل",
        f"🤍 {name} — حاجة من الجنة",
        f"🕊️ {name} — اسمع بقلبك مش بس ودنيك",
        f"💎 {name} — لو عايز تبدأ يومك حلو",
        f"🤲 {name} — هتفهم حاجة جديدة",
        f"🌿 {name} — عشان الدنيا مش كلها شغل",
        f"😊 {name} — استماع = فرحة",
        f"💛 {name} — لازم تسمع ده",
        f"🤍 {name} — عشان كل الناس بتحبك",
        f"🕊️ {name} — الساعة دي ليك إنت",
        f"💎 {name} — بصوت عمار الخطيب مش هتلاقي شبهه",
        f"🌿 {name} — الجنة اللي جوه قلبك",
        f"🤲 {name} — اسمع وابقى قول شكرا",
        f"✨ {name} — أول حاجة حلوة تسمعها النهارده",
        f"❤️ {name} — القرآن عرفني بيك",
        f"🫶 {name} — اسمع وابقى ورينا",
        f"😊 {name} — هتعشق السورة دي",
        f"💛 {name} — عشان الخير اللي جواك",
        f"🌙 {name} — دقيقة بس تعيشها",
        f"🤍 {name} — حاجة من الجنة جت هنا",
        f"🕊️ {name} — القرآن بيطمنك أهي",
        f"💎 {name} — الجمال اللي في وشك",
        f"🤲 {name} — عشانك إنت بالذات",
        f"🌿 {name} — هتفتح باب جديد جواك",
        f"✨ {name} — اسمع وانسى اللي وراك",
        f"❤️ {name} — دلوقت بتسمع القرآن",
        f"🫶 {name} — عشان محدش عملك كده قبل كده",
        f"😊 {name} — لو الدنيا اتقلبت اسمع دي",
        f"💛 {name} — السورة اللي قلبي كان مستناها",
        f"🌙 {name} — بصوت عمار الخطيب ياللي ما بتحوش في حاجة",
        f"🤍 {name} — خد نفس عميق واسمع",
        f"🕊️ {name} — عشان روحك محتاجة",
        f"💎 {name} — السورة اللي ممكن تغير حياتك",
        f"🤲 {name} — اسمع وقول يا رب",
        f"🌿 {name} — لما تيجي تقفل تلفونك",
        f"✨ {name} — آخر حاجة حلوة قبل ما تنام",
        f"❤️ {name} — عشان جميل",
        f"🫶 {name} — اسمع واسمع تانى",
        f"😊 {name} — عشان بجد بتحب الخير",
        f"💛 {name} — دقيقة هتفرق في باقي يومك",
        f"🌙 {name} — سورة بقالها 1400 سنة بتهدي الناس",
        f"🤍 {name} — اسمع وقل يا الله",
        f"🕊️ {name} — السكينة جت هنا",
        f"💎 {name} — عشان الواحد محتاج يطمن كده",
        f"🤲 {name} — اسمع وابقى نورنا",
        f"🌿 {name} — الجو ده مالوش ثاني",
        f"✨ {name} — خليك هنا دلوقتي",
        f"❤️ {name} — عشان ربنا جميل",
        f"🫶 {name} — اسمع وقول من قلبك",
        f"😊 {name} — هتحبها والله",
        f"💛 {name} — عشان كلنا محتاجين كده",
        f"🌙 {name} — بصوت عمار الخطيب خليك قريب",
        f"🤍 {name} — اسمع وانت ماسك تلفونك دلوقتي",
        f"🕊️ {name} — عشان الواحد بيتعب",
        f"💎 {name} — تلاوة تعيش بيها",
        f"🤲 {name} — اسمع وقول آمين",
        f"🌿 {name} — دقيقة بس تغير المود",
        f"✨ {name} — لو عايز سلام اسمع ده",
    ]
    import random
    short_name = random.choice(title_templates)

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
        video_url = upload_to_release(video_path, key, int(start), int(end))

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
    import shutil

    release_tag = "latest-short"
    asset_name = f"short-surah-{key}-{start:03d}-{end:03d}.mp4"

    try:
        # Copy video to temp file with better name
        tmp_path = os.path.join("build", asset_name)
        shutil.copy2(video_path, tmp_path)

        # Create release if it doesn't exist (silent if already exists)
        subprocess.run(
            ["gh", "release", "create", release_tag,
             "--title", "Latest Short",
             "--notes", "Auto-generated Short video (overwritten each run)"],
            capture_output=True, text=True, timeout=30
        )

        # Upload (overwrite existing asset with same name)
        result = subprocess.run(
            ["gh", "release", "upload", release_tag, tmp_path,
             "--clobber"],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            print(f"Release upload warning: {result.stderr[:200]}")
            return ""

        # Get the download URL (the mp4 asset)
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
