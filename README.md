# Bulk Media SEO Tool — Shopify & WordPress

[Arabic version below](#-arabic)

## Overview

An advanced Python GUI tool for **Shopify** store owners and **WordPress/WooCommerce** merchants. Automates the entire media SEO optimization pipeline — images AND videos:

| Feature | Shopify | WordPress |
|---|---|---|
| Read CSV | Shopify CSV | WooCommerce CSV |
| Download Images | Auto-download | Manual / Local files |
| Compress Images -> WebP | Yes | Yes |
| Compress Videos -> WEBM | Yes (auto) | Yes (auto) |
| Video Thumbnails | Yes (WebP) | Yes (WebP) |
| SEO Filename (images) | Yes | Yes |
| SEO Filename (videos) | Yes | Yes |
| Alt Text | Yes | Yes (reference file) |
| Export CSV | `products_seo_optimized.csv` | `products_wp_optimized.csv` |
| Upload to Store | Shopify API (optional) | Manual (by design) |
| Direct Images/Videos/ZIP | Yes | Yes |
| FFmpeg Auto-Install | Yes (first run) | Yes (first run) |
| Mobile Video Rotation Fix | Yes | Yes |

---

## How to Run

### Quick Start (Windows):
Double-click `تشغيل_الأداة.bat`

### Via Command Line:
```bash
py shopify_gui.py
```

---

## Requirements (One-time setup)

1. **Python 3.8+** from [python.org](https://www.python.org/downloads/) — check **"Add Python to PATH"**
2. **Install dependencies:**
```bash
pip install requests Pillow tqdm rarfile
```

> **FFmpeg** is auto-installed on first video processing. No manual setup needed!
> RAR extraction requires WinRAR or UnRAR on your system. ZIP is natively supported.

---

## GUI Guide

The GUI has **two tabs** at the top:

### Shopify Tab
- **Download + Compress**: Reads Shopify CSV -> downloads all media -> SEO-optimizes -> compresses
- **Download Only**: Downloads images for external processing
- **Compress Only**: Compresses media already on your machine
- **Input**: Shopify CSV export OR direct images/videos/ZIP/RAR OR folder
- **Output**: Compressed WebP images + WEBM videos + thumbnails + `products_seo_optimized.csv`

### WordPress Tab *(No API — 100% local)*
- **Input**: WooCommerce CSV export OR direct images/videos/ZIP/RAR OR folder
- **Processing**: SEO renaming + WebP/WEBM compression
- **Output**:
  - `wp_compressed_images/` — WebP images + WEBM videos + WebP thumbnails
  - `products_wp_optimized.csv` — WooCommerce import-ready CSV
  - `wp_alt_text_reference.csv` — Alt text table for manual copy
  - `wp_alt_text_reference.html` — Beautiful HTML table (click to copy alt text)
  - `wp_seo_optimization_log.csv` — Detailed optimization log
  - `wp_report.txt` — Summary report

---

## Video Processing (NEW)

### How it works:
1. **Select media** — images, videos, or mixed (the tool auto-classifies)
2. **Press START** — FFmpeg auto-installs on first run (~80 MB, one-time)
3. **Output:**
   - Videos compressed to **WEBM** (VP9 + Opus) — best format for web/PageSpeed
   - Auto-generated **thumbnails** in WebP — for `<video poster="...">`
   - SEO filenames and alt text for videos
   - Mobile/TikTok/social media videos **rotation fixed automatically**

### Video settings:
| Setting | Value |
|---|---|
| Output format | WEBM (VP9 codec) |
| Quality | CRF 31 (balanced — no pixelation) |
| Max resolution | 1080p |
| Max FPS | 30 |
| Audio | Opus 128kbps stereo |
| Thumbnail | WebP, quality 85% |

### Supported video formats:
`.mp4 .mov .avi .mkv .webm .m4v .wmv .flv .3gp .mts .ts`

---

## Project Files

### Core — Shopify
| File | Purpose |
|---|---|
| `shopify_gui.py` | Main GUI (Shopify + WordPress tabs) |
| `shopify_image_downloader.py` | Shopify engine: CSV parser, downloader, compressor, uploader |
| `seo_helpers.py` | Shopify SEO: filenames, alt text, WebP compression engine |

### Core — WordPress
| File | Purpose |
|---|---|
| `wordpress_image_processor.py` | WordPress engine: WooCommerce CSV parser, compressor, exporters |
| `wordpress_seo_helpers.py` | WordPress SEO: general-purpose filenames & alt text (60-90 chars) |

### Core — Video (Shared)
| File | Purpose |
|---|---|
| `video_helpers.py` | Video engine: WEBM compression, thumbnails, rotation fix, FFmpeg auto-install |
| `ffmpeg_bin/` | Portable FFmpeg (auto-downloaded on first run) |

### Config & Docs
| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `تشغيل_الأداة.bat` | Windows launcher |
| `PROJECT_ARCHITECTURE.md` | Technical docs for developers & AI |
| `USER_GUIDE.md` | Detailed usage guide |

---

## SEO Standards Applied

### Images (both platforms)
- Filenames: `{slug}-{descriptor}.webp`
- Alt text: < 125 chars (Shopify) / 60-90 chars (WordPress)
- Size: 80-200 KB target
- Format: WebP always
- EXIF rotation: auto-fixed

### Videos (both platforms)
- Filenames: `{slug}-product-video.webm`
- Alt text: "Watch {product} review video" etc.
- Format: WEBM (VP9 + Opus)
- Quality: CRF 31 (balanced)
- Rotation: auto-fixed (mobile/TikTok/social media)
- Thumbnail: `{slug}-video-poster.webp`

---

## Output Structure

```
compressed_images/ (or wp_compressed_images/)
+-- product-name/
    |-- product-name-main-product-image.webp     (image)
    |-- product-name-detail-view.webp             (image)
    |-- product-name-product-video.webm           (video)
    |-- product-name-video-poster.webp            (thumbnail)
    +-- product-name-product-demo.webm            (video)
```

---

*

# Arabic

## Bulk Media SEO Tool

## نظرة عامة

اداة بايثون بواجهة رسومية لـ **شوبيفاي** و**ووردبريس/ووكومرس**:

**الميزات الرئيسية:**
1. **تحميل الصور** — من ملف CSV شوبيفاي تلقائيا
2. **تسمية SEO ذكية** — اسماء ملفات احترافية + Alt Text تلقائي
3. **ضغط صور WebP** — الحجم المثالي (80-200 KB) بافضل جودة
4. **ضغط فيديو WEBM** — VP9 + Opus بجودة عالية بدون بكسلة (جديد!)
5. **صور مصغرة تلقائية** — لكل فيديو صورة WebP للـ poster (جديد!)
6. **تصحيح دوران الفيديو** — فيديوهات الموبايل/تيك توك متطلعش مقلوبة (جديد!)
7. **تثبيت FFmpeg تلقائي** — بدون تدخل من المستخدم (جديد!)
8. **صور مباشرة وفيديوهات وZIP/RAR** — بدون الحاجة لملف CSV
9. **CSV جاهز للاستيراد** — لشوبيفاي وووكومرس
10. **مرجع Alt Text HTML** — انسخ الـ Alt Text بنقرة

## تشغيل الاداة

**الطريقة الاسهل:** دوبل كليك على `تشغيل_الأداة.bat`

```bash
py shopify_gui.py
```

## الواجهة — تبويبان

### تبويب Shopify
- تحميل + ضغط من CSV شوبيفاي
- دعم صور + فيديوهات + ZIP/RAR ومجلدات
- تصدير CSV محسن جاهز للرفع

### تبويب WordPress *(بدون API — على الكمبيوتر فقط)*
- قراءة CSV ووكومرس او صور/فيديوهات مباشرة
- ضغط WebP + WEBM + تسمية SEO
- تصدير Alt Text كـ CSV + HTML
- تصدير CSV محسن لاستيراد ووكومرس

## معالجة الفيديو (جديد!)

- **FFmpeg يتثبت تلقائي** اول مرة بس (~80 ميجا) — مش محتاج تعمل حاجة
- **الفيديوهات بتتضغط WEBM** — افضل صيغة للويب و PageSpeed
- **صورة مصغرة WebP** لكل فيديو — لـ `<video poster>`
- **تصحيح الدوران** — فيديوهات الموبايل والسوشيال ميديا متطلعش مقلوبة
- **الاداة بتصنف تلقائي** — صور ولا فيديوهات مش محتاج تفصلهم

## متطلبات التشغيل

```bash
pip install requests Pillow tqdm rarfile
```

> FFmpeg بيتثبت تلقائي اول مرة تشغل فيها فيديو. مش محتاج تعمل حاجة يدوي!

> مصمم للوصول للمراتب الاولى في نتائج محركات البحث — شوبيفاي وووردبريس
