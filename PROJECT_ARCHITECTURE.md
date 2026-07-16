# Bulk Image SEO Tool — Shopify & WordPress
**Project Architecture & Technical Documentation**

This document is the authoritative reference for the project's architecture, data flow, and components.
Designed for developers and AI assistants working on this codebase.

---

## 📁 File Structure

```
project/
│
├── 🖥️  ENTRY POINT
│   └── shopify_gui.py              Main GUI — Shopify tab + WordPress tab
│
├── 🛒  SHOPIFY ENGINE (original — unchanged)
│   ├── shopify_image_downloader.py CSV parser + downloader + compressor + uploader
│   └── seo_helpers.py              Shopify SEO: filenames, alt text, compression
│
├── 🌐  WORDPRESS ENGINE (new — fully standalone)
│   ├── wordpress_image_processor.py WooCommerce CSV parser + compressor + exporters
│   └── wordpress_seo_helpers.py    WordPress SEO: general-purpose for any product type
│
├── ⚙️  CONFIG
│   ├── requirements.txt            pip dependencies
│   ├── تشغيل_الأداة.bat           Windows double-click launcher
│   └── .gitignore
│
└── 📚  DOCS
    ├── README.md                   User documentation (EN + AR)
    └── PROJECT_ARCHITECTURE.md     This file
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    shopify_gui.py                        │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  🛒 Shopify Tab  │    │  🌐 WordPress Tab        │   │
│  │  (original UI)   │    │  (new — blue accents)    │   │
│  └────────┬─────────┘    └───────────┬──────────────┘   │
└───────────┼──────────────────────────┼──────────────────┘
            │                          │
            ▼                          ▼
┌───────────────────┐      ┌────────────────────────────┐
│  shopify_image_   │      │  wordpress_image_           │
│  downloader.py    │      │  processor.py               │
│                   │      │                             │
│ ShopifyCSVParser  │      │ WooCommerceCSVParser        │
│ ImageDownloader   │      │ WordPressImageCompressor    │
│ ImageCompressor   │      │ WooCommerceCSVExporter      │
│ ShopifyCSVExporter│      │ WordPressAltTextExporter    │
│ ShopifyUploader   │      │ WordPressReportGenerator    │
│ ReportGenerator   │      └────────────┬───────────────┘
└───────────┬───────┘                   │
            │                           │
            ▼                           ▼
┌───────────────────┐      ┌────────────────────────────┐
│  seo_helpers.py   │◄─────│  uses compress_image_seo() │
│                   │      │  (shared compression engine)│
│ compress_image_seo│      └────────────────────────────┘
│ generate_seo_*    │
│ generate_alt_text │      ┌────────────────────────────┐
│ SEOLogger         │      │  wordpress_seo_helpers.py  │
└───────────────────┘      │                            │
                           │ wp_build_slug()             │
                           │ wp_generate_seo_filename()  │
                           │ wp_generate_alt_text()      │
                           │ wp_extract_product_info()   │
                           │ WPSEOLogger                 │
                           └────────────────────────────┘
```

**Key design principle:** The WordPress modules are **completely independent** of Shopify modules,
except for one shared function: `compress_image_seo()` from `seo_helpers.py` (the compression engine).

---

## 🔑 Component Details

### 1. GUI (`shopify_gui.py`)

**Tab System:**
- Tab bar at top with two buttons: `🛒 Shopify` | `🌐 WordPress`
- `_switch_platform(platform)` — shows/hides the correct frame
- Each tab has its own: scrollable content, log widget, progress bar, status label

**Shared infrastructure:**
- Single `log_queue` (thread-safe) used by both tabs
- `_poll_log()` routes messages: 2-tuple → Shopify log, 3-tuple `(msg, tag, "wp")` → WordPress log
- `_file_row()` helper reused by both tabs for file/folder pickers

**Threading model:**
- Heavy work runs in `threading.Thread(daemon=True)`
- GUI updates via `self.root.after(0, ...)` — never direct widget access from threads

---

### 2. Shopify Engine (`shopify_image_downloader.py`)

| Class | Responsibility |
|---|---|
| `ShopifyCSVParser` | Reads Shopify product export CSV. Handles multi-row products (one row per image). Extracts SEO metadata: vendor, body HTML, olfactory family, scent, season, gender, sizes. |
| `ImageDownloader` | Parallel download with `ThreadPoolExecutor`. Retry + exponential backoff. Resume support (skips existing files). |
| `ImageCompressor` | Routes to `compress_all_seo()` (primary) or `compress_all()` (legacy). Builds SEO task list from products dict. |
| `ShopifyCSVExporter` | Updates `Image Src` and `Image Alt Text` columns in original CSV. Outputs `products_seo_optimized.csv`. |
| `ShopifyUploader` | Shopify Admin API upload. Rate-limit aware (0.6s delay). Deletes old images before uploading new ones. |
| `ReportGenerator` | Writes `report.txt` with full statistics. |

**Shopify CSV format:**
```
Handle | Title | Image Src | Image Position | Image Alt Text | Vendor | ...
```
Each image = one row. Same Handle across multiple rows = same product.

---

### 3. Shopify SEO (`seo_helpers.py`)

| Function | Description |
|---|---|
| `compress_image_seo()` | **SHARED** — WebP compression engine. Target 80-200KB, max 2048px. Used by both Shopify and WordPress. |
| `build_unique_slug()` | Builds unique slug from Handle, preserving variant markers (edp/parfum/50ml). Adds 4-char MD5 suffix. |
| `extract_brand_and_perfume()` | Extracts brand + perfume name from Handle/Title/Vendor. Priority: Vendor → KNOWN_BRANDS → "by" pattern → first word. |
| `generate_seo_filename()` | `{slug}-{descriptor}.webp` — perfume-specific descriptors. |
| `generate_alt_text()` | <125 chars. Position-specific natural sentences. Integrates olfactory_family, scent, season, gender, sizes, notes. |
| `SEOLogger` | Records old→new filename mapping + alt text + compression stats to CSV. |

**Shopify SEO focus:** perfume/fragrance industry. Uses domain-specific `KNOWN_BRANDS`, `VARIANT_MARKERS`, `POSITION_DESCRIPTORS`.

---

### 4. WordPress Engine (`wordpress_image_processor.py`)

| Class | Responsibility |
|---|---|
| `WooCommerceCSVParser` | Reads WooCommerce product export CSV. One row per product. Images in `Images` column separated by `\|`. Extracts: ID, SKU, Name, Categories, Tags, Short description, Description. |
| `WordPressImageCompressor` | Calls `compress_image_seo()` for compression. Uses `wordpress_seo_helpers` for naming. Builds SEO task list from products dict. Supports `compress_direct_images()` (no CSV). |
| `WooCommerceCSVExporter` | Updates `Images` column with new filenames (pipe-separated). Outputs `products_wp_optimized.csv`. |
| `WordPressAltTextExporter` | Exports two files: `wp_alt_text_reference.csv` and `wp_alt_text_reference.html` (click-to-copy table). |
| `WordPressReportGenerator` | Writes `wp_report.txt`. |

**WooCommerce CSV format:**
```
ID | Type | SKU | Name | Short description | Description | Categories | Tags | Images
```
All images in one cell, pipe-separated: `img1.jpg|img2.jpg|img3.jpg`

---

### 5. WordPress SEO (`wordpress_seo_helpers.py`)

**Design goal:** General-purpose — works for ANY product type (electronics, clothing, food, perfumes, etc.)

| Function | Description |
|---|---|
| `wp_build_slug(name, sku, categories)` | Slug from product name + SKU. Strips noise words. Adds 4-char MD5 suffix for uniqueness. |
| `wp_extract_product_info(name, categories, short_description)` | Returns `{product_name, main_category, description_snippet}`. Handles Arabic text gracefully (skips it). |
| `wp_generate_seo_filename(slug, position, total)` | `{slug}-{descriptor}.webp`. General descriptors: `main-product-image`, `detail-view`, `gallery-view`, etc. |
| `wp_generate_alt_text(product_name, category, position, total, metadata)` | **60-90 characters** (WordPress/Yoast/RankMath optimum). Position-specific natural sentences. No "image of". |
| `WPSEOLogger` | Records all optimization details to `wp_seo_optimization_log.csv`. |

**WordPress vs Shopify SEO differences:**

| | Shopify (`seo_helpers.py`) | WordPress (`wordpress_seo_helpers.py`) |
|---|---|---|
| **Industry** | Perfumes/Fragrances | Any industry (general) |
| **Alt text length** | < 125 chars | **60-90 chars** |
| **Slug source** | Handle (Shopify-specific) | Name + SKU |
| **Brand extraction** | `extract_brand_and_perfume()` | `wp_extract_product_info()` |
| **Descriptors** | `perfume-decant`, `fragrance-detail` | `main-product-image`, `detail-view` |
| **Noise words** | Fragrance-specific (`edp`, `ml`, `decant`) | General (`product`, `item`, `new`, `image`) |

---

## 🔄 Data Flow

### Shopify Flow (CSV mode):
```
Shopify CSV → ShopifyCSVParser → products{}
    → ImageDownloader (parallel) → downloaded_images/
    → ImageCompressor.compress_all_seo() → compressed_images/
        └─ compress_image_seo() [seo_helpers]
        └─ generate_seo_filename() [seo_helpers]
        └─ generate_alt_text() [seo_helpers]
    → ShopifyCSVExporter → products_seo_optimized.csv
    → SEOLogger → seo_optimization_log.csv
    → ReportGenerator → report.txt
```

### WordPress Flow (CSV mode):
```
WooCommerce CSV → WooCommerceCSVParser → products{}
    → WordPressImageCompressor.compress_all_seo()
        └─ compress_image_seo() [seo_helpers — shared engine]
        └─ wp_generate_seo_filename() [wordpress_seo_helpers]
        └─ wp_generate_alt_text() [wordpress_seo_helpers]
    → WooCommerceCSVExporter → products_wp_optimized.csv
    → WordPressAltTextExporter → wp_alt_text_reference.csv + .html
    → WPSEOLogger → wp_seo_optimization_log.csv
    → WordPressReportGenerator → wp_report.txt
```

### Direct Images Flow (both platforms):
```
Local images / ZIP / RAR
    → Extract to temp folder
    → Build pseudo products{} from folder names
    → Same compression pipeline as CSV mode
    → Cleanup temp folder
```

---

## 📤 Output Files Summary

| File | Mode | Description |
|---|---|---|
| `compressed_images/` | Shopify | Shopify WebP images |
| `wp_compressed_images/` | WordPress | WordPress WebP images |
| `products_seo_optimized.csv` | Shopify | Import-ready Shopify CSV |
| `products_wp_optimized.csv` | WordPress | Import-ready WooCommerce CSV |
| `seo_optimization_log.csv` | Shopify | Old→New names + alt text log |
| `wp_seo_optimization_log.csv` | WordPress | Old→New names + alt text log |
| `wp_alt_text_reference.csv` | WordPress | Alt text table (for manual copy) |
| `wp_alt_text_reference.html` | WordPress | Click-to-copy alt text HTML page |
| `report.txt` | Shopify | Operation summary |
| `wp_report.txt` | WordPress | Operation summary |

---

## 🔧 Adding Support for a New Platform

To add a 3rd platform (e.g., Magento, Wix):
1. Create `{platform}_seo_helpers.py` — SEO naming + alt text for that platform
2. Create `{platform}_image_processor.py` — CSV parser + compressor + exporters
3. Add a new tab in `shopify_gui.py` following the WordPress tab pattern
4. **Do NOT modify** `seo_helpers.py` or `shopify_image_downloader.py`

The `compress_image_seo()` function in `seo_helpers.py` is the shared compression engine — import it directly.

---

*Generated for internal reference and AI context. Last updated: 2026-07*
