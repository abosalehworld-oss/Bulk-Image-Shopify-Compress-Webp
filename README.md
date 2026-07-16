# 🛒🌐 Bulk Image SEO Tool — Shopify & WordPress

[اللغة العربية بالأسفل ⬇️](#-النسخة-العربية)

## 📋 Overview

An advanced Python GUI tool for **Shopify** store owners and **WordPress/WooCommerce** merchants. Automates the entire image SEO optimization pipeline — no API required for WordPress:

| Feature | Shopify | WordPress |
|---|---|---|
| Read CSV | ✅ Shopify CSV | ✅ WooCommerce CSV |
| Download Images | ✅ Auto-download | ➖ Manual / Local files |
| Compress → WebP | ✅ | ✅ |
| SEO Filename | ✅ | ✅ |
| Alt Text | ✅ | ✅ Reference file for manual copy |
| Export CSV | ✅ `products_seo_optimized.csv` | ✅ `products_wp_optimized.csv` |
| Upload to Store | ✅ Shopify API (optional) | ❌ Manual (by design for safety) |
| Direct Images/ZIP | ✅ | ✅ |

---

## 🖥️ How to Run

### Quick Start (Windows):
Double-click `تشغيل_الأداة.bat` ✅

### Via Command Line:
```bash
py shopify_gui.py
```

---

## ⚙️ Requirements (One-time setup)

1. **Python 3.8+** from [python.org](https://www.python.org/downloads/) — check **"Add Python to PATH"**
2. **Install dependencies:**
```bash
pip install requests Pillow tqdm rarfile
```
> RAR extraction requires WinRAR or UnRAR on your system. ZIP is natively supported.

---

## 🎯 GUI Guide

The GUI has **two tabs** at the top:

### 🛒 Shopify Tab
- **Download + Compress**: Reads Shopify CSV → downloads all images → SEO-optimizes → compresses to WebP
- **Download Only**: Downloads images for external processing
- **Compress Only**: Compresses images already on your machine
- **Input**: Shopify CSV export OR direct images/ZIP/RAR
- **Output**: Compressed WebP images + `products_seo_optimized.csv` (ready to import into Shopify)

### 🌐 WordPress Tab *(No API — 100% local)*
- **Input**: WooCommerce CSV export OR direct images/ZIP/RAR
- **Processing**: SEO renaming + WebP compression (80-200 KB target)
- **Output**:
  - 📁 `wp_compressed_images/` — WebP images with SEO filenames
  - 📄 `products_wp_optimized.csv` — WooCommerce import-ready CSV
  - 📋 `wp_alt_text_reference.csv` — Alt text table for manual copy
  - 🌐 `wp_alt_text_reference.html` — Beautiful HTML table (click to copy alt text)
  - 📊 `wp_seo_optimization_log.csv` — Detailed optimization log
  - 📝 `wp_report.txt` — Summary report

---

## 📁 Project Files

### Core — Shopify
| File | Purpose |
|---|---|
| `shopify_gui.py` | Main GUI (Shopify + WordPress tabs) |
| `shopify_image_downloader.py` | Shopify engine: CSV parser, downloader, compressor, uploader |
| `seo_helpers.py` | Shopify SEO: filenames, alt text, compression engine |

### Core — WordPress *(New — Standalone)*
| File | Purpose |
|---|---|
| `wordpress_image_processor.py` | WordPress engine: WooCommerce CSV parser, compressor, exporters |
| `wordpress_seo_helpers.py` | WordPress SEO: general-purpose filenames & alt text (60-90 chars) |

### Config & Docs
| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `تشغيل_الأداة.bat` | Windows launcher |
| `PROJECT_ARCHITECTURE.md` | Technical docs for developers & AI |

---

## 📊 SEO Standards Applied

### Shopify Images
- Filenames: `brand-perfume-name-descriptor.webp`
- Alt text: < 125 characters (Shopify limit)
- Size: 80–150 KB target
- Max dimension: 2000px

### WordPress Images
- Filenames: `product-name-slug-main-product-image.webp`
- Alt text: **60–90 characters** (WordPress/Yoast/RankMath optimum)
- Size: 80–200 KB target
- Max dimension: 2048px
- Format: WebP always

---

*

# 🛒🌐 النسخة العربية

## 📋 نظرة عامة

أداة بايثون بواجهة رسومية لـ **شوبيفاي** و**ووردبريس/ووكومرس** — بدون API للووردبريس:

**الميزات الرئيسية:**
1. **📥 تحميل الصور** — من ملف CSV شوبيفاي تلقائياً
2. **🧠 تسمية SEO ذكية** — أسماء ملفات احترافية + Alt Text تلقائي
3. **🗜️ ضغط WebP** — الحجم المثالي (80-200 KB) بأفضل جودة
4. **📦 صور مباشرة وZIP/RAR** — بدون الحاجة لملف CSV
5. **📄 CSV جاهز للاستيراد** — لشوبيفاي وووكومرس
6. **📋 مرجع Alt Text HTML** — انسخ الـ Alt Text بنقرة لمكتبة الميديا

## 🖥️ تشغيل الأداة

**الطريقة الأسهل:** دوبل كليك على `تشغيل_الأداة.bat`

```bash
py shopify_gui.py
```

## 🎯 الواجهة — تبويبان

### 🛒 تبويب Shopify
- تحميل + ضغط من CSV شوبيفاي
- دعم ZIP/RAR وصور مباشرة
- تصدير CSV محسّن جاهز للرفع

### 🌐 تبويب WordPress *(بدون API — على الكمبيوتر فقط)*
- قراءة CSV ووكومرس أو صور مباشرة
- ضغط WebP + تسمية SEO
- تصدير Alt Text كـ CSV + HTML جميل (للنسخ اليدوي في مكتبة الميديا)
- تصدير CSV محسّن لاستيراد ووكومرس

## ⚙️ متطلبات التشغيل

```bash
pip install requests Pillow tqdm rarfile
```

> 🛠️ **مصمم للوصول للمراتب الأولى في نتائج محركات البحث — شوبيفاي وووردبريس** 🚀
