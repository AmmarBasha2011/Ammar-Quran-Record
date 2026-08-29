# 🛠️ Tools — Ammar Quran Record

مجموعة الأدوات اللي بتشغّل أتمتة التلاوات: التقطيع، النشر، رفع YouTube، والإحصائيات.

---

## 📑 الفهرس

| الأداة | الوظيفة | يُشغَّل |
|---|---|---|
| `quran_split.py` | تقطيع سورة لآيات (whisper + forced alignment) | محلياً |
| `add_surah.py` | نشر سورة في الـ repo + تحديث available.json | محلياً |
| `recut_ayahs.py` | إعادة تقطيع آيات معيّنة | محلياً |
| `rebuild_available.py` | إعادة بناء available.json من الـ reports | محلياً |
| `get_youtube_token.py` | OAuth one-time لجلب refresh_token | محلياً (مرة واحدة) |
| `upload_youtube.py` | رفع Short مباشرة على YouTube | CI (video-autopost) |
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

**ملاحظة:** الأداة بتفصل الاستعاذة/البسملة عن الآية 1 تلقائياً قبل الـ alignment.

---

## 📤 2. add_surah.py — النشر

ينسخ ملفات السورة + `_report.json` للـ repo ويحدّث `available.json`.

```bash
python tools/add_surah.py 044
```

---

## ✂️ 3. recut_ayahs.py — إعادة التقطيع

يُعيد تقطيع آيات معيّنة من سورة (بعد تصحيح أو مراجعة).

```bash
python tools/recut_ayahs.py 103 1 3   # أعد تقطيع آيات 1-3 من سورة 103
```

---

## 🔄 4. rebuild_available.py — إعادة بناء available.json

يقرأ كل `_report.json` ويبني `available.json` بالمقاييس الصحيحة.

```bash
python tools/rebuild_available.py
```

> **ملاحظة:** السكربت ده محلي (مش مرفوع في CI) — لو احتجت إعادة بناء متزامنة استخدم الـ Python one-liner في الـ terminal.

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

**الـ redirect URI:** لازم تضيف `http://localhost:8899/` في Google Cloud Console → OAuth client.

---

## 📹 6. upload_youtube.py — الرفع المباشر

يرفع Short على YouTube عبر OAuth (refresh_token من Secrets).

```bash
python tools/upload_youtube.py KEY NAME START END
# مثال: python tools/upload_youtube.py 024 النور 1 3
```

يقرأ من البيئة: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

---

## 📊 7. youtube_stats.py — الإحصائيات

يقرأ إحصائيات القناة ويقارن Shorts vs Long-form.

```bash
python tools/youtube_stats.py
```

**المخرجات:**
- عدد المشتركين / المشاهدات / الفيديوهات
- متوسط المشاهدات والـ likes لـ Shorts vs Long-form
- Top 5 Shorts و Top 5 Long-form

---

## 🔐 أسرار GitHub (Secrets)

الـ workflow `video-autopost.yml` بيقرأ من GitHub Secrets:

| السر | الوظيفة |
|---|---|
| `YT_CLIENT_ID` | معرّف OAuth client |
| `YT_CLIENT_SECRET` | سر OAuth client |
| `YT_REFRESH_TOKEN` | توكن التحديث (بيفضل صالح للأبد — يتحط مرة واحدة) |

> ⚠️ **لا ترفع الأسرار في الكود** — استخدم GitHub Secrets فقط.

---

## 📦 المتطلبات

```bash
pip install faster-whisper google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
# + ffmpeg (للنظام)
```

---

<div align="center">
<sub>INEX Team • 2026</sub>
</div>
