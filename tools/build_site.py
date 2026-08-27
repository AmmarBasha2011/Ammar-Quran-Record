# -*- coding: utf-8 -*-
"""Build a beautiful INEX-DNA-2026 styled static audio site (site/index.html)
from available.json + links.json.

Features:
  - Jet-black bg (#020617), orchid/royal-blue gradient tiles (INEX DNA 2026)
  - RTL Arabic, Tajawal font
  - Live client-side search (surah name or number)
  - Collapsible per-surah <details> with per-ayah <audio> players
  - Weak-ayah badges

Output: ./site/index.html  (published by pages-site.yml to GitHub Pages)
"""
import os, json

REPO = "."
av = json.load(open("available.json", encoding="utf-8"))
links = json.load(open("links.json", encoding="utf-8")).get("links", {})
repo_name = os.environ.get("GITHUB_REPOSITORY", "AmmarBasha2011/Ammar-Quran-Record")
raw = f"https://raw.githubusercontent.com/{repo_name}/main"

surahs = av.get("surahs", {})
total = av.get("total_ayat", 0)
total_s = len(surahs)

# load ayah texts (for display under each player)
try:
    _idx = json.load(open("tools/quran_norm_index.json", encoding="utf-8"))
    def ayah_text(key, a):
        try:
            return _idx[key]["texts"][a - 1]
        except Exception:
            return ""
except Exception:
    def ayah_text(key, a):
        return ""

cards = []
for key in sorted(surahs, key=int):
    s = surahs[key]
    name = links.get(key, {}).get("name", "?")
    n = s.get("ayahs", 0)
    weak = set(s.get("weak_ayahs", []))
    ayahs = []
    for a in range(1, n + 1):
        url = f"{raw}/{key}/{a:03d}.mp3"
        cls = " w" if a in weak else ""
        txt = ayah_text(key, a)
        txt_html = (f'<div class="a-txt">{txt}</div>' if txt else "")
        ayahs.append(
            f'<div class="ayah{cls}" id="a{key}-{a:03d}">'
            f'<span class="a-n">{a:03d}</span>'
            f'<div class="a-body"><audio controls preload="none" src="{url}"></audio>{txt_html}</div>'
            f'</div>')
    wbadge = (f'<span class="badge-w">⚠ {len(weak)} weak</span>' if weak else
              '<span class="badge-ok">✓ clean</span>')
    cards.append(
        f'<details class="surah" data-name="{name}" data-num="{int(key)}">\n'
        f'  <summary>\n'
        f'    <span class="s-num">{int(key):03d}</span>\n'
        f'    <span class="s-name">{name}</span>\n'
        f'    <span class="s-meta">{n} آية</span>\n'
        f'    {wbadge}\n'
        f'  </summary>\n'
        f'  <div class="ayah-grid">{"".join(ayahs)}</div>\n'
        f'</details>')

HEAD_CSS = """\
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تلاوات عمار الخطيب — INEX</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#020617; --primary:#9333EA; --secondary:#3B82F6; --accent:#A855F7;
    --text:#fff; --muted:#94a3b8; --tile:linear-gradient(135deg,#9333EA,#A855F7);
    --card:rgba(30,41,59,.55); --card-brd:rgba(168,85,247,.25);
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:'Tajawal',system-ui,sans-serif;background:var(--bg);
    color:var(--text);min-height:100vh;
    background-image:radial-gradient(1200px 600px at 80% -10%,rgba(147,51,234,.18),transparent),
      radial-gradient(1000px 500px at 0% 0%,rgba(59,130,246,.15),transparent);}
  header{text-align:center;padding:48px 16px 28px;}
  .logo{font-size:2.6rem;font-weight:800;letter-spacing:.5px;
    background:var(--tile);-webkit-background-clip:text;background-clip:text;color:transparent;}
  .sub{color:var(--muted);margin-top:6px;font-size:1.05rem}
  .stats{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:20px 0 8px}
  .stat{background:var(--card);border:1px solid var(--card-brd);border-radius:14px;
    padding:12px 20px;backdrop-filter:blur(8px);min-width:120px}
  .stat b{display:block;font-size:1.5rem;background:var(--tile);
    -webkit-background-clip:text;background-clip:text;color:transparent;}
  .stat span{color:var(--muted);font-size:.85rem}
  .search{max-width:560px;margin:22px auto 8px;position:relative}
  .search input{width:100%;padding:15px 46px 15px 18px;font-size:1.05rem;font-family:inherit;
    border-radius:14px;border:1px solid var(--card-brd);background:rgba(15,23,42,.7);
    color:#fff;outline:none;transition:.2s;}
  .search input:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(168,85,247,.2)}
  .search::before{content:"🔍";position:absolute;right:16px;top:50%;transform:translateY(-50%);opacity:.6}
  .count{text-align:center;color:var(--muted);font-size:.9rem;margin-bottom:24px}
  main{max-width:1000px;margin:0 auto;padding:0 16px 60px}
  .surah{background:var(--card);border:1px solid var(--card-brd);border-radius:16px;
    margin:10px 0;backdrop-filter:blur(8px);overflow:hidden;transition:.2s}
  .surah:hover{border-color:var(--accent)}
  .surah[open]{border-color:var(--primary)}
  summary{display:flex;align-items:center;gap:14px;cursor:pointer;padding:16px 18px;list-style:none}
  summary::-webkit-details-marker{display:none}
  .s-num{font-family:Consolas,monospace;background:var(--tile);color:#fff;border-radius:10px;
    padding:6px 10px;font-weight:700;font-size:.95rem}
  .s-name{font-weight:700;font-size:1.2rem;flex:1}
  .s-meta{color:var(--muted);font-size:.9rem}
  .badge-w{background:rgba(234,179,8,.15);color:#facc15;border:1px solid rgba(234,179,8,.4);
    border-radius:20px;padding:3px 10px;font-size:.8rem}
  .badge-ok{background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.4);
    border-radius:20px;padding:3px 10px;font-size:.8rem}
  .ayah-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px;
    padding:14px 18px 18px}
  .ayah{display:flex;align-items:flex-start;gap:10px;background:rgba(2,6,23,.55);
    border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:8px 12px}
  .ayah.w{border-color:rgba(234,179,8,.45)}
  .a-n{font-family:Consolas,monospace;color:var(--accent);min-width:30px;font-weight:700;padding-top:6px}
  .a-body{flex:1;display:flex;flex-direction:column;gap:6px}
  .ayah audio{width:100%;height:34px}
  .a-txt{direction:rtl;text-align:right;font-size:.92rem;line-height:1.7;color:#e2e8f0;
    background:rgba(15,23,42,.5);border-right:3px solid var(--accent);
    padding:8px 12px;border-radius:8px}
  .empty{text-align:center;color:var(--muted);padding:40px;display:none}
  footer{text-align:center;color:var(--muted);font-size:.82rem;padding:30px;border-top:1px solid var(--card-brd)}
  footer a{color:var(--accent);text-decoration:none}
  audio::-webkit-media-controls-panel{background:#1e293b}
</style>
</head>
<body>
<header>
  <div class="logo">🕌 تلاوات عمار الخطيب</div>
  <div class="sub">مكتبة القرآن الكريم بصوت القارئ عمار الخطيب — INEX Team</div>
  <div class="stats">
    <div class="stat"><b>__TOTAL_S__</b><span>سورة منشورة</span></div>
    <div class="stat"><b>__TOTAL_AYAT__</b><span>آية مقطوعة</span></div>
    <div class="stat"><b>128</b><span>kbps جودة</span></div>
  </div>
  <div class="search"><input id="q" type="search" placeholder="ابحث باسم السورة أو رقمها... (مثل: النمل أو 27)" autocomplete="off"></div>
  <div class="count" id="count"></div>
</header>
<main id="list">
__CARDS__
<div class="empty" id="empty">لا توجد سورة مطابقة للبحث</div>
</main>
<footer>
  جميع الحقوق محفوظة للقارئ <b>عمار الخطيب</b> • المشروع تحت إشراف <a href="https://github.com/AmmarBasha2011">INEX Team</a> • 2026
</footer>
"""

SCRIPT = """\
<script>
  var q=document.getElementById('q'),list=document.getElementById('list'),
    empty=document.getElementById('empty'),count=document.getElementById('count'),
    all=[].slice.call(list.querySelectorAll('.surah'));
  function filter(){
    var t=q.value.trim().toLowerCase(),tq=null,shown=0;
    tq=(t!==''&&!isNaN(t))?+t:null;
    all.forEach(function(c){
      var name=c.dataset.name.toLowerCase(),num=+c.dataset.num;
      var ok=(!t)||name.indexOf(t)>-1||(tq!==null&&num===tq);
      c.style.display=ok?'':'none'; if(ok)shown++;
    });
    empty.style.display=shown?'none':'block';
    count.textContent=shown+' من '+all.length+' سورة';
  }
  q.addEventListener('input',filter); filter();

  // Deep-link: open surah card + scroll to + play ayah from #a035-011
  function goAyah(){
    var h=location.hash.match(/^#a([0-9]{3})-([0-9]{3})$/);
    if(!h) return;
    var num=parseInt(h[1],10);
    var card=document.querySelector('.surah[data-num="'+num+'"]');
    if(!card) return;
    card.open=true;
    function focusAyah(){
      var el=document.getElementById('a'+h[1]+'-'+h[2]);
      if(!el) return;
      el.scrollIntoView({behavior:'smooth',block:'center'});
      el.style.outline='3px solid #A855F7';
      var a=el.querySelector('audio');
      if(a) a.play().catch(function(){});
    }
    // wait a tick for the <details> content to render, then focus + play
    setTimeout(focusAyah, 300);
    setTimeout(focusAyah, 900);
  }
  window.addEventListener('hashchange',goAyah);
  window.addEventListener('load',goAyah);
  document.addEventListener('DOMContentLoaded',goAyah);
</script>
</body>
</html>
"""

html = (HEAD_CSS
        .replace("__TOTAL_S__", str(total_s))
        .replace("__TOTAL_AYAT__", str(total))
        .replace("__CARDS__", "".join(cards))
        + SCRIPT)

os.makedirs("site", exist_ok=True)
open("site/index.html", "w", encoding="utf-8").write(html)
print(f"Built INEX-styled site/index.html with {total_s} surahs")
