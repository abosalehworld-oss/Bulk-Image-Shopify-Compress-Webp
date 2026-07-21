# Bulk Media SEO Tool — Shopify & WordPress
**Project Architecture & Technical Documentation**

This document is the authoritative reference for the project's architecture, data flow, and components.
Designed for developers and AI assistants working on this codebase.

---

## File Structure

```
project/
|
|-- ENTRY POINT
|   +-- shopify_gui.py              Main GUI — Shopify tab + WordPress tab
|
|-- SHOPIFY ENGINE
|   |-- shopify_image_downloader.py CSV parser + downloader + compressor + uploader
|   +-- seo_helpers.py              Shopify SEO: filenames, alt text, compression
|
|-- WORDPRESS ENGINE
|   |-- wordpress_image_processor.py WooCommerce CSV parser + compressor + exporters
|   +-- wordpress_seo_helpers.py    WordPress SEO: general-purpose for any product type
|
|-- VIDEO ENGINE (NEW)
|   +-- video_helpers.py            Video compression (WEBM/VP9), thumbnails (WebP),
|                                    SEO naming, rotation fix, FFmpeg auto-install
|
|-- AUTO-INSTALLED (first run)
|   +-- ffmpeg_bin/                 Portable FFmpeg (auto-downloaded, ~80 MB)
|       |-- ffmpeg.exe
|       +-- ffprobe.exe
|
|-- CONFIG
|   |-- requirements.txt            pip dependencies
|   |-- .bat                        Windows double-click launcher
|   +-- .gitignore
|
+-- DOCS
    |-- README.md                   User documentation (EN + AR)
    |-- USER_GUIDE.md               Detailed usage guide
    +-- PROJECT_ARCHITECTURE.md     This file
```

---

## Architecture Overview

```
+----------------------------------------------------------+
|                    shopify_gui.py                          |
|  +------------------+    +----------------------------+   |
|  |  Shopify Tab      |    |  WordPress Tab             |   |
|  |  (original UI)    |    |  (new -- blue accents)     |   |
|  +--------+----------+    +------------+--------------+   |
+-----------+----------------------------+------------------+
            |                            |
            v                            v
+---------------------+      +------------------------------+
|  shopify_image_      |      |  wordpress_image_             |
|  downloader.py       |      |  processor.py                 |
|                      |      |                               |
| ShopifyCSVParser     |      | WooCommerceCSVParser          |
| ImageDownloader      |      | WordPressImageCompressor      |
| ImageCompressor      |      | WooCommerceCSVExporter        |
| ShopifyCSVExporter   |      | WordPressAltTextExporter      |
| ShopifyUploader      |      | WordPressReportGenerator      |
| ReportGenerator      |      +---------------+---------------+
+-----------+----------+                      |
            |                                 |
            v                                 v
+---------------------+      +------------------------------+
|  seo_helpers.py      |<-----|  uses compress_image_seo()    |
|                      |      |  (shared compression engine)  |
| compress_image_seo   |      +------------------------------+
| generate_seo_*       |
| generate_alt_text    |      +------------------------------+
| SEOLogger            |      |  wordpress_seo_helpers.py     |
+-----------+----------+      |                               |
            |                 | wp_build_slug()               |
            |                 | wp_generate_seo_filename()    |
            v                 | wp_generate_alt_text()        |
+---------------------+      +------------------------------+
|  video_helpers.py    |
|  (NEW - shared)      |<---- Used by BOTH Shopify & WordPress
|                      |
| auto_install_ffmpeg  |  Auto-downloads FFmpeg on first run
| compress_video_seo   |  WEBM (VP9+Opus) compression
| generate_video_      |  Video thumbnail (WebP)
|   thumbnail          |
| get_video_info       |  Detects rotation metadata
| generate_video_      |  SEO filenames & alt text
|   seo_filename       |
| generate_video_      |
|   alt_text           |
+----------------------+
```

**Key design principles:**
- WordPress modules are **completely independent** of Shopify modules, except for `compress_image_seo()`.
- `video_helpers.py` is **shared** by both platforms — imported by both `shopify_image_downloader.py` and `wordpress_image_processor.py`.
- FFmpeg is **auto-installed** on first use — no manual setup required.

---

## Component Details

### 1. GUI (`shopify_gui.py`)

**Tab System:**
- Tab bar at top with two buttons: Shopify | WordPress
- `_switch_platform(platform)` — shows/hides the correct frame
- Each tab has its own: scrollable content, log widget, progress bar, status label

**Input Sources (both tabs):**
- CSV: Shopify/WooCommerce product export
- Direct Images: Manual file selection (images + videos + ZIP/RAR)
- Folder: Select a folder with subfolders per product

**Media handling:**
- Detects images AND videos from file extensions
- Auto-groups media by source folder (each folder = one product)
- Shows count: "Folder: X (15 images, 3 videos)"

**FFmpeg auto-install:**
- On START, if video files detected and FFmpeg missing → auto-download
- Download happens once, saved to `ffmpeg_bin/` locally
- Progress shown in the log panel

**Threading model:**
- Heavy work runs in `threading.Thread(daemon=True)`
- GUI updates via `self.root.after(0, ...)` — never direct widget access from threads

---

### 2. Shopify Engine (`shopify_image_downloader.py`)

| Class | Responsibility |
|---|---|
| `ShopifyCSVParser` | Reads Shopify product export CSV. Handles multi-row products (one row per image). Extracts SEO metadata: vendor, body HTML, olfactory family, scent, season, gender, sizes. |
| `ImageDownloader` | Parallel download with `ThreadPoolExecutor`. Retry + exponential backoff. Resume support (skips existing files). |
| `ImageCompressor` | Routes to `compress_all_seo()` (primary) or `compress_all()` (legacy). Builds SEO task list from products dict. **Detects and processes videos alongside images.** |
| `ShopifyCSVExporter` | Updates `Image Src` and `Image Alt Text` columns in original CSV. Outputs `products_seo_optimized.csv`. |
| `ShopifyUploader` | Shopify Admin API upload. Rate-limit aware (0.6s delay). |
| `ReportGenerator` | Writes `report.txt` with full statistics. |

---

### 3. Shopify SEO (`seo_helpers.py`)

| Function | Description |
|---|---|
| `compress_image_seo()` | **SHARED** — WebP compression engine. Target 80-200KB, max 2048px. Used by both Shopify and WordPress. Includes EXIF rotation fix. |
| `build_unique_slug()` | Builds unique slug from Handle, preserving variant markers. Adds 4-char MD5 suffix. |
| `extract_brand_and_perfume()` | Extracts brand + perfume name from Handle/Title/Vendor. |
| `generate_seo_filename()` | `{slug}-{descriptor}.webp` — perfume-specific descriptors. |
| `generate_alt_text()` | < 125 chars. Position-specific natural sentences. |
| `SEOLogger` | Records old-to-new filename mapping + alt text + compression stats to CSV. |

---

### 4. WordPress Engine (`wordpress_image_processor.py`)

| Class | Responsibility |
|---|---|
| `WooCommerceCSVParser` | Reads WooCommerce CSV. One row per product. Images in `Images` column separated by pipe. |
| `WordPressImageCompressor` | Uses `compress_image_seo()` for images and `compress_video_seo()` for videos. Uses `wordpress_seo_helpers` for naming. **Handles mixed image+video input.** |
| `WooCommerceCSVExporter` | Updates `Images` column with new filenames. |
| `WordPressAltTextExporter` | Exports `wp_alt_text_reference.csv` and `.html` (click-to-copy). |
| `WordPressReportGenerator` | Writes `wp_report.txt`. |

---

### 5. WordPress SEO (`wordpress_seo_helpers.py`)

**Design goal:** General-purpose — works for ANY product type.

| Function | Description |
|---|---|
| `wp_build_slug(name, sku, categories)` | Slug from product name + SKU. Strips noise words. |
| `wp_extract_product_info(...)` | Returns `{product_name, main_category, description_snippet}`. |
| `wp_generate_seo_filename(...)` | `{slug}-{descriptor}.webp`. General descriptors. |
| `wp_generate_alt_text(...)` | **60-90 characters** (WordPress/Yoast/RankMath optimum). |
| `WPSEOLogger` | Records optimization details to CSV. |

---

### 6. Video Engine (`video_helpers.py`) — NEW

**Design goal:** Process videos for web (PageSpeed optimization) with the same SEO quality as images.

| Function | Description |
|---|---|
| `check_ffmpeg()` | Checks PATH, local `ffmpeg_bin/`, common Windows paths. |
| `auto_install_ffmpeg()` | **Auto-downloads** portable FFmpeg (~80 MB) from gyan.dev to `ffmpeg_bin/`. One-time, no admin needed. |
| `get_video_info()` | Extracts duration, dimensions, FPS, codec, **rotation metadata**. Returns display dimensions (after rotation). |
| `compress_video_seo()` | WEBM (VP9 + Opus). CRF 31 balanced. Max 1080p, 30fps. **Fixes rotation** for mobile/TikTok/social media videos. |
| `generate_video_thumbnail()` | Extracts frame from video, saves as WebP. **Rotation-aware.** |
| `generate_video_seo_filename()` | `{slug}-product-video.webm`, `{slug}-product-demo.webm`, etc. |
| `generate_video_thumbnail_filename()` | `{slug}-video-poster.webp` |
| `generate_video_alt_text()` | SEO alt text for video: "Watch {product} review video" etc. |

**Rotation handling (critical for mobile videos):**
```
1. get_video_info() detects rotation from:
   - side_data_list (modern MP4/MOV)
   - tags.rotate (legacy MP4/MOV)

2. compress_video_seo() applies:
   - -noautorotate flag (disable FFmpeg's auto-rotate)
   - transpose filter (manual rotation: 90, 180, 270 degrees)
   - -metadata:s:v rotate=0 (clear rotation tag from output)

3. Same logic applied to thumbnail extraction
```

**Supported video formats:**
`.mp4 .mov .avi .mkv .webm .m4v .wmv .flv .3gp .mts .ts`

---

## Data Flow

### Shopify Flow (CSV mode):
```
Shopify CSV -> ShopifyCSVParser -> products{}
    -> ImageDownloader (parallel) -> downloaded_images/
    -> ImageCompressor.compress_all_seo() -> compressed_images/
        +-- Images: compress_image_seo() [seo_helpers]
        +-- Videos: compress_video_seo() [video_helpers]
        +-- Thumbnails: generate_video_thumbnail() [video_helpers]
        +-- generate_seo_filename() / generate_video_seo_filename()
        +-- generate_alt_text() / generate_video_alt_text()
    -> ShopifyCSVExporter -> products_seo_optimized.csv
    -> SEOLogger -> seo_optimization_log.csv
    -> ReportGenerator -> report.txt
```

### WordPress Flow (CSV mode):
```
WooCommerce CSV -> WooCommerceCSVParser -> products{}
    -> WordPressImageCompressor.compress_all_seo()
        +-- Images: compress_image_seo() [seo_helpers -- shared engine]
        +-- Videos: compress_video_seo() [video_helpers -- shared engine]
        +-- Thumbnails: generate_video_thumbnail() [video_helpers]
        +-- wp_generate_seo_filename() / generate_video_seo_filename()
        +-- wp_generate_alt_text() / generate_video_alt_text()
    -> WooCommerceCSVExporter -> products_wp_optimized.csv
    -> WordPressAltTextExporter -> wp_alt_text_reference.csv + .html
    -> WPSEOLogger -> wp_seo_optimization_log.csv
    -> WordPressReportGenerator -> wp_report.txt
```

### Direct Images/Videos Flow (both platforms):
```
Local media (images + videos) / ZIP / RAR / Folder
    -> Extract to temp folder
    -> Auto-detect: images vs videos (by extension)
    -> Build pseudo products{} from folder names
    -> Auto-install FFmpeg if needed (first time only)
    -> Same compression pipeline as CSV mode
    -> Cleanup temp folder
```

---

## Output Files Summary

| File | Mode | Description |
|---|---|---|
| `compressed_images/` | Shopify | WebP images + WEBM videos + WebP thumbnails |
| `wp_compressed_images/` | WordPress | WebP images + WEBM videos + WebP thumbnails |
| `ffmpeg_bin/` | Shared | Auto-installed FFmpeg (portable, one-time) |
| `products_seo_optimized.csv` | Shopify | Import-ready Shopify CSV |
| `products_wp_optimized.csv` | WordPress | Import-ready WooCommerce CSV |
| `seo_optimization_log.csv` | Shopify | Old-to-New names + alt text log |
| `wp_seo_optimization_log.csv` | WordPress | Old-to-New names + alt text log |
| `wp_alt_text_reference.csv` | WordPress | Alt text table (for manual copy) |
| `wp_alt_text_reference.html` | WordPress | Click-to-copy alt text HTML page |
| `report.txt` | Shopify | Operation summary |
| `wp_report.txt` | WordPress | Operation summary |

---

## Adding Support for a New Platform

To add a 3rd platform (e.g., Magento, Wix):
1. Create `{platform}_seo_helpers.py` — SEO naming + alt text for that platform
2. Create `{platform}_image_processor.py` — CSV parser + compressor + exporters
3. Add a new tab in `shopify_gui.py` following the WordPress tab pattern
4. **Do NOT modify** `seo_helpers.py` or `shopify_image_downloader.py`

Shared engines (import directly):
- `compress_image_seo()` from `seo_helpers.py` — image compression
- `compress_video_seo()` from `video_helpers.py` — video compression

---

*Generated for internal reference and AI context. Last updated: 2026-07*
