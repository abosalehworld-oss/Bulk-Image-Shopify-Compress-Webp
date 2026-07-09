# Shopify Bulk Image Compressor & SEO Optimizer
**Project Architecture & Technical Documentation**

This document serves as a comprehensive guide to the project's architecture, data flow, and core components. It is designed to help any developer or AI assistant understand the system deeply.

## 📁 Directory & File Structure

- `shopify_gui.py`: The main entry point. A graphical user interface (GUI) built with `tkinter`.
- `shopify_image_downloader.py`: The core engine containing logic for CSV parsing, multi-threaded downloading, compression routing, and reporting.
- `seo_helpers.py`: The "Intelligence" module responsible for SEO optimizations, filename generation, and Alt Text crafting.
- `requirements.txt`: Python dependencies (`requests`, `Pillow`, `tqdm`, `rarfile`).
- `تشغيل_الأداة.bat`: Windows batch script for easy launching.
- `README.md`: User-facing documentation.

## 🏗️ Core Components & Workflow

### 1. User Interface (`shopify_gui.py`)
- **Dual Input Modes**: 
  - **CSV Mode**: Reads a Shopify product export CSV.
  - **Local Mode**: Accepts raw image files (`.jpg`, `.png`, etc.) or archives (`.zip`, `.rar`) directly.
- **Execution**: Uses Python's `threading` to run the heavy processing `_run()` method in the background without freezing the GUI. Communicates with the main thread via a thread-safe `queue` for live logging.
- **Local Mode Processing**: When archives/images are provided, it extracts them into a temporary folder (`temp_extracted_images_to_compress`), assigns the parent folder name (or the image's base name) as the "Product Handle/Title", and feeds it into the core engine to ensure SEO rules still apply even without a CSV.

### 2. Core Engine (`shopify_image_downloader.py`)
- **`ShopifyCSVParser`**: Parses the raw Shopify CSV. Intelligently extracts handles, titles, image URLs, and SEO metadata (vendor, tags, olfactory family, fragrance, target gender, sizes).
- **`ImageDownloader`**: Uses `requests.Session` with `ThreadPoolExecutor` for fast, parallel downloading. Implements retry logic and exponential backoff.
- **`ImageCompressor`**: Routes the images to the compression logic.
  - `compress_all_seo()`: The primary pipeline. Maps original images to SEO-optimized filenames, delegates compression to `seo_helpers`, and records changes in `SEOLogger`.
- **`ShopifyCSVExporter`**: Generates a new `products_seo_optimized.csv` where `Image Src` and `Image Alt Text` are updated to match the newly generated WebP files.
- **`ReportGenerator`**: Produces a `report.txt` summarizing download success/failures, total bytes saved, and compression ratios.

### 3. SEO Intelligence (`seo_helpers.py`)
- **Filename Optimization (`generate_seo_filename`)**: Strips noise words (e.g., "decant", "ml", "edp"), uses only hyphens, and appends position numbers (e.g., `brand-perfume-name-1.webp`).
- **Alt Text Generation (`generate_alt_text`)**: Constructs natural, descriptive sentences (< 125 chars). Example: "Buy Brand Perfume Name, a Floral scent for Men." Incorporates metadata dynamically.
- **Compression (`compress_image_seo`)**: 
  - Forces WebP format.
  - Resizes dimensions > 2000px using Lanczos resampling.
  - Dynamically adjusts quality to hit a target file size of 80 KB - 150 KB (ideal for Shopify LCP performance).

## 🔄 Data Flow (End-to-End)
1. **Input**: User selects CSV + Download/Compress Folders OR Local Files (ZIP/RAR/Images) + Compress Folder.
2. **Pre-processing**: 
   - *CSV*: Parse into `products` dictionary.
   - *Local*: Extract/Copy to temp folder, build pseudo `products` dictionary from folder/file names.
3. **Downloading (CSV only)**: Parallel download of all images to the target download folder.
4. **Compression & SEO**: Traverse images, determine new SEO names, compress to WebP (target 80-150KB), and generate Alt Text.
5. **Output**: 
   - WebP images in the Compress folder.
   - `seo_optimization_log.csv` (Detailed mapping of old names to new names).
   - `products_seo_optimized.csv` (Only in CSV mode).
   - `report.txt` (Summary of the operation).
   - *Cleanup*: Deletes temp folder if Local mode was used.

---
*Generated for internal reference and AI context.*
