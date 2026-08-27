# -*- coding: utf-8 -*-
"""Build a static audio site (site/index.html) from available.json + links.json.

Each surah is a collapsible <details> block; each ayah has an <audio> player
pointing at the raw.githubusercontent.com MP3. Output goes to ./site so the
pages-site workflow can publish it.
"""
import os, json

REPO = "."
av = json.load(open("available.json", encoding="utf-8"))
links = json.load(open("links.json", encoding="utf-8")).get("links", {})
repo_name = os.environ.get("GITHUB_REPOSITORY", "AmmarBasha2011/Ammar-Quran-Record")
raw = f"https://raw.githubusercontent.com/{repo_name}/main"

surahs = av.get("surahs", {})
total = av.get("total_ayat", 0)

items = []
for key in sorted(surahs, key=int):
    s = surahs[key]
    name = links.get(key, {}).get("name", "?")
    n = s.get("ayahs", 0)
    ayahs = []
    for a in range(1, n + 1):
        url = f"{raw}/{key}/{a:03d}.mp3"
        ayahs.append(f'<li><span class="n">{a:03d}</span>'
                     f'<audio controls preload="none" src="{url}"></audio></li>')
    weak = s.get("weak_ayahs", [])
    wlabel = f'<span class="w">⚠ weak: {weak}</span>' if weak else ""
    items.append(
        f'<details class="surah">\n'
        f'  <summary><b>{key}</b> {name} '
        f'<span class="c">({n} آية)</span>{wlabel}</summary>\n'
        f'  <ul class="ayahs">{"".join(ayahs)}</ul>\n'
        f'</details>')

html = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تلاوات عمار الخطيب</title>
<style>
  body {{ font-family: system-ui, "Segoe UI", sans-serif; background:#0f1115; color:#e6e6e6; margin:0; padding:20px; }}
  h1 {{ text-align:center; }}
  .meta {{ text-align:center; color:#9aa; margin-bottom:20px; }}
  .surah {{ background:#1a1d24; border:1px solid #2a2e38; border-radius:8px; margin:8px 0; padding:10px 14px; }}
  summary {{ cursor:pointer; font-size:1.1em; }}
  .c {{ color:#9aa; font-size:.85em; }}
  .w {{ color:#e8a23a; font-size:.8em; margin-inline-start:8px; }}
  .ayahs {{ list-style:none; padding:0; margin:10px 0 0; display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:6px; }}
  .ayahs li {{ display:flex; align-items:center; gap:8px; background:#14171d; padding:6px 8px; border-radius:6px; }}
  .n {{ color:#7d8; font-variant-numeric:tabular-nums; min-width:28px; }}
  audio {{ flex:1; height:32px; }}
</style>
</head>
<body>
<h1>🕌 تلاوات عمار الخطيب</h1>
<div class="meta">{len(surahs)} سورة • {total} آية • جاهزة للاستماع المباشر</div>
{''.join(items)}
<footer style="text-align:center;color:#666;margin-top:30px;font-size:.8em">جميع الحقوق محفوظة للقارئ عمار الخطيب • INEX Team • 2026</footer>
</body>
</html>'''

os.makedirs("site", exist_ok=True)
open("site/index.html", "w", encoding="utf-8").write(html)
print(f"Built site/index.html with {len(surahs)} surahs")
