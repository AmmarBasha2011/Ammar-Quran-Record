# 🛠️ Tools — Ammar Quran Record

مجموعة الأدوات اللي بتشغّل أتمتة التلاوات: التقطيع، النشر، رفع YouTube، وإعادة الرفع، والإحصائيات.

---

## 📑 الفهرس

| الأداة | الوظيفة | يُشغَّل |
|---|---|---|
| `quran_split.py` | تقطيع سورة لآيات (whisper + forced alignment) | محلياً |
| `add_surah.py` | نشر سورة في الـ repo + تحديث available.json | محلياً |
| `recut_ayahs.py` | إعادة تقطيع آيات معيّنة | محلياً |
| `rebuild_available.py` | إعادة بناء available.json من الـ reports | محلياً |
| `get_youtube_token.py` | OAuth one-time لجلب refresh_token | محلياً (مرة واحدة) |
| `upload_youtube.py` | رفع Short مباشرة على YouTube | CI |
| `pick_best.py` | يختار أعلى Short من القناة لإعادة رفعه | CI |
| `youtube_stats.py` | قراءة إحصائيات القناة + مقارنة Shorts/Long | محلياً / CI |

---

## 🔪 1. quran_split.py — التقطيع

يقطّع ملف صوت سورة كاملة لآيات منفصلة باستخدام faster-whisper + forced alignment.

```bash
python tools/quran_split.py PATH_TO_AUDIO.mp3 044 OUTPUT_DIR --beam 5
```

**المعاملات:**
- `PATH_TO_AUDIO.mp3` — ملف السورة الكاملة
- `044` — رقم السورة (3 خانات)
- `OUTPUT_DIR` — مجلد الإخراج (مثلاً `cut_one/044/`)
- `--beam 5` — جودة المحاذاة (أعلى = أدق وأبطأ)

**المخرجات:**
- `OUTPUT_DIR/001.mp3`, `002.mp3`, ... — الآيات
- `OUTPUT_DIR/_report.json` — تقرير الجودة (sim/weak_ayahs)

**آلية العمل:**
1. whisper يفرّغ الصوت كلمة بكلمة (بيتعلّم نطق القارئ)
2. forced alignment يربط كل كلمة بوقت بدايتها/نهايتها
3. نقارن بالنص الرسمي للقرآن → similarity score لكل آية
4. الآيات اللي sim < 0.75 بتتعلّم `weak` في الـ report

> **ملاحظة:** الأداة بتفصل الاستعاذة/البسملة عن الآية 1 تلقائياً قبل الـ alignment (عشان ما تتحسبش كجزء من الآية).

---

## 📤 2. add_surah.py — النشر

ينسخ ملفات السورة + `_report.json` للـ repo ويحدّث `available.json`.

```bash
python tools/add_surah.py 044
```

**المخرجات:**
- ينسخ `044/*.mp3` + `044/_report.json` → `repo/044/`
- يحدّث `repo/available.json` بمقاييس السورة

---

## ✂️ 3. recut_ayahs.py — إعادة التقطيع

يُعيد تقطيع آيات معيّنة من سورة (بعد تصحيح أو مراجعة).

```bash
python tools/recut_ayahs.py 103 1 3   # أعد تقطيع آيات 1-3 من سورة 103
```

**المعاملات:** `SURAH START END` (أرقام الآيات)

---

## 🔄 4. rebuild_available.py — إعادة بناء available.json

يقرأ كل `_report.json` ويبني `available.json` بالمقاييس الصحيحة (total_ayat, min_sim, avg_sim, weak_ayahs, manual_revise).

```bash
python tools/rebuild_available.py
```

> **ملاحظة:** السكربت ده محلي (مش مرفوع في CI). لو احتجت إعادة بناء متزامنة في الـ terminal استخدم Python one-liner.

---

## 🔑 5. get_youtube_token.py — OAuth (مرة واحدة)

يطلب موافقة YouTube ويعطيك `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

```bash
pip install google-auth-oauthlib google-auth
python tools/get_youtube_token.py
```

**الصلاحيات المطلوبة:**
- `https://www.googleapis.com/auth/youtube.upload`
- `https://www.googleapis.com/auth/youtube.readonly`

> ⚠️ `ytanalytics.readonly` **مرفوض** لـ OAuth client عادي (بيحتاج Content Owner). استخدم `youtube.readonly` بدلاً منه.

**الـ redirect URI:** لازم تضيف `http://localhost:8899/` في Google Cloud Console → OAuth client (Desktop app).

**المخرجات:**
```
YT_CLIENT_ID=960444193801-...apps.googleusercontent.com
YT_CLIENT_SECRET=GOCSPX-...
YT_REFRESH_TOKEN=1//03...
```
→ تحطهم في **GitHub Secrets** (الـ refresh_token بيفضل صالح للأبد — يتحط مرة واحدة).

---

## 📹 6. upload_youtube.py — الرفع المباشر

يرفع Short على YouTube عبر OAuth (refresh_token من Secrets).

```bash
python tools/upload_youtube.py KEY NAME START END
# مثال: python tools/upload_youtube.py 024 النور 1 3
```

**المعاملات:**
- `KEY` — رقم السورة (مثل 024)
- `NAME` — اسم السورة (مثل النور)
- `START`, `END` — رقم أول/آخر آية

**يقرأ من البيئة:** `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

**العنوان/الوصف اللي بيتكتب:**
```
العنوان: 🎧 سورة {NAME} | الآيات {START}–{END} | تلاوة عمار الخطيب
الوصف: تلاوة مباركة بصوت القارئ عمار الخطيب ✨
        📖 سورة {NAME} ({KEY}) — الآيات {START}–{END}

        🔊 استمع للآية مباشرة:
        https://raw.githubusercontent.com/.../main/{KEY}/{START:03d}.mp3

        📚 المكتبة الكاملة (76 سورة مقسّمة آية آية):
        https://github.com/AmmarBasha2011/Ammar-Quran-Record

        🌐 الموقع: https://ammarbasha2011.github.io/Ammar-Quran-Record/

        🤲 اللهم اجعل القرآن ربيع قلوبنا. شاركه مع من تحب.

        #قرآن #تلاوة #عمار_الخطيب #سورة_{NAME} #الآيات_{START}_{END} #اسلام #Shorts #قرآن_كريم
الوسوم: [قرآن, تلاوة, عمار_الخطيب, اسلام, Shorts, سورة_{NAME}, قرآن_كريم, تلاوات]
```

**المخرجات:**
```
YOUTUBE_VIDEO_ID=XXXX
https://youtube.com/shorts/XXXX
```

> الفيديو بيتعامل كـ **Short** تلقائياً لأنه عمودي (9:16) وأقل من 3 دقايق.

---

## 🏆 7. pick_best.py — اختيار أحسن فيديو

يقرأ القناة، يجمع أعلى 10 Shorts بالمشاهدات، ويختار واحد عشوائي لإعادة رفعه.

```bash
python tools/pick_best.py
```

**يقرأ من البيئة:** `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

**الآلية:**
1. يجيب uploads playlist للقناة
2. لكل فيديو: يحسب المدة (Min < 3 = Short) ويقرأ المشاهدات
3. يفلتر Shorts اللي عناوينها بصيغتنا (`سورة X (KEY) - الآية A-B`)
4. ياخد top 10 بالمشاهدات، يختار واحد عشوائي
5. يكتب `pick.txt` (KEY, NAME, START, END) عشان `video-reupload.yml` يبنيه

> لو مفيش Shorts قديمة: بيكتب `pick.txt` فاضي والـ workflow بيتخطّى الرفع.

---

## 📊 8. youtube_stats.py — الإحصائيات

يقرأ إحصائيات القناة ويقارن Shorts vs Long-form.

```bash
python tools/youtube_stats.py
```

**يقرأ من البيئة:** `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

**المخرجات:**
- عدد المشتركين / المشاهدات / الفيديوهات
- متوسط المشاهدات والـ likes لـ Shorts vs Long-form
- Top 5 Shorts و Top 5 Long-form

**مثال النتيجة:**
```
Shorts   avg views: 68  | avg likes: 5
Long-form avg views: 31 | avg likes: 1
```

---

## 🔐 أسرار GitHub (Secrets)

الـ workflows `video-autopost.yml` و `video-reupload.yml` بيقرأوا من GitHub Secrets:

| السر | الوظيفة |
|---|---|
| `YT_CLIENT_ID` | معرّف OAuth client |
| `YT_CLIENT_SECRET` | سر OAuth client |
| `YT_REFRESH_TOKEN` | توكن التحديث (بيفضل صالح للأبد — يتحط مرة واحدة) |

> ⚠️ **لا ترفع الأسرار في الكود** — استخدم GitHub Secrets فقط. الـ refresh_token بيفضل صالح للأبد فمحتاجش تعيد عمل OAuth غير لو الغيت الصلاحية يدوياً.

---

## 📦 المتطلبات

```bash
pip install faster-whisper google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
# + ffmpeg (للنظام)
```

---

## 🔄 سير العمل اليومي (مثال)

```
1. تسجّل سورة جديدة على يوتيوب
2. تنزّلها: yt-dlp -x --audio-format mp3 "URL" → cut_one/XXX/XXX_source.mp3
3. تقطّعها: python tools/quran_split.py cut_one/XXX/XXX_source.mp3 XXX cut_one/XXX --beam 5
4. تنشرها: python tools/add_surah.py XXX
5. ترفع للـ repo: git add -A && git commit && git push
6. الـ CI يفحص (validate/drift/weak-report) وينشر الموقع + RSS أوتوماتيك
7. video-autopost يرفع Short كل 4 ساعات
8. video-reupload يعيد رفع أحسن Short مرة يومياً
```

---

<div align="center">
<sub>INEX Team • 2026</sub>
</div>
