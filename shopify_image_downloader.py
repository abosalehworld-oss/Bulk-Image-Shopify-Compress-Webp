#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
أداة تحميل وضغط ورفع صور منتجات شوبيفاي بالجملة
Shopify Product Image Bulk Downloader, Compressor & Uploader

تقرأ ملف CSV المُصدّر من متجر شوبيفاي، تُحمّل جميع صور المنتجات،
تُنظمها في مجلدات حسب المنتج، تضغطها، وترفعها مرة أخرى.
"""

import csv
import os
import sys
import time
import json
import base64
import hashlib
import logging
import argparse
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote

try:
    from seo_helpers import (
        clean_handle_for_seo, extract_brand_and_perfume,
        generate_seo_filename, generate_alt_text,
        compress_image_seo, SEOLogger, _strip_html, _extract_notes_snippet,
        build_unique_slug
    )
    SEO_AVAILABLE = True
except ImportError:
    SEO_AVAILABLE = False

try:
    from video_helpers import (
        check_ffmpeg, compress_video_seo, generate_video_thumbnail,
        generate_video_seo_filename, generate_video_thumbnail_filename,
        generate_video_alt_text, is_video_file, is_image_file,
        classify_media_files, VIDEO_EXTENSIONS, format_duration, format_size
    )
    VIDEO_AVAILABLE = check_ffmpeg()
except ImportError:
    VIDEO_AVAILABLE = False

# إصلاح ترميز الكونسول على ويندوز لدعم العربي والإيموجي
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("❌ مكتبة requests غير مثبتة. شغّل: pip install requests")
    sys.exit(1)

try:
    from PIL import Image, ImageOps
except ImportError:
    print("❌ مكتبة Pillow غير مثبتة. شغّل: pip install Pillow")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("❌ مكتبة tqdm غير مثبتة. شغّل: pip install tqdm")
    sys.exit(1)


# ─────────────────────────────────────────────
# إعداد الألوان للطباعة في الكونسول
# ─────────────────────────────────────────────
class Colors:
    """ANSI color codes for console output."""
    if sys.platform == "win32":
        os.system("")  # تفعيل ANSI على ويندوز
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner():
    """طباعة شعار الأداة."""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║        🛒  أداة صور شوبيفاي بالجملة  🛒                    ║
║        Shopify Bulk Image Tool                              ║
║──────────────────────────────────────────────────────────────║
║  📥 تحميل  │  🗜️ ضغط  │  ☁️ رفع  │  📊 تقرير              ║
╚══════════════════════════════════════════════════════════════╝
{Colors.RESET}"""
    print(banner)


# ─────────────────────────────────────────────
# 1. قراءة ملف CSV من شوبيفاي
# ─────────────────────────────────────────────
class ShopifyCSVParser:
    """يقرأ ملف CSV المُصدّر من شوبيفاي ويجمع صور كل منتج مع بيانات SEO."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.products = {}  # handle -> {title, vendor, images[], metadata...}
        self.headers = []   # رؤوس الأعمدة الأصلية
        self.logger = logging.getLogger("CSVParser")

    def _detect_encoding(self) -> str:
        """محاولة اكتشاف ترميز الملف تلقائيًا."""
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1256', 'windows-1256']
        for enc in encodings:
            try:
                with open(self.csv_path, 'r', encoding=enc) as f:
                    f.read(1024)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return 'utf-8'

    def _find_column(self, headers: list, possible_names: list) -> int:
        """البحث عن عمود بأسماء محتملة مختلفة (case-insensitive)."""
        headers_lower = [h.strip().lower() for h in headers]
        for name in possible_names:
            if name.lower() in headers_lower:
                return headers_lower.index(name.lower())
        return -1

    def _safe_get(self, row, idx, default=''):
        """استخراج قيمة من صف بأمان."""
        if idx != -1 and idx < len(row):
            return row[idx].strip()
        return default

    def parse(self) -> dict:
        """
        قراءة الملف وتجميع صور كل منتج مع بيانات SEO.
        شوبيفاي يضع كل صورة إضافية في صف منفصل بنفس الـ Handle.
        """
        if not os.path.exists(self.csv_path):
            print(f"{Colors.RED}❌ الملف غير موجود: {self.csv_path}{Colors.RESET}")
            sys.exit(1)

        encoding = self._detect_encoding()
        self.logger.info(f"ترميز الملف: {encoding}")

        with open(self.csv_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f)
            self.headers = next(reader)
            headers = self.headers

            # ── الأعمدة الأساسية ──
            handle_idx = self._find_column(headers, ['Handle', 'handle'])
            title_idx = self._find_column(headers, ['Title', 'title', 'Name', 'name'])
            image_src_idx = self._find_column(headers, ['Image Src', 'image src', 'Image URL', 'image url'])
            variant_img_idx = self._find_column(headers, ['Variant Image', 'variant image'])
            img_position_idx = self._find_column(headers, ['Image Position', 'image position'])
            img_alt_idx = self._find_column(headers, ['Image Alt Text', 'image alt text'])

            # ── أعمدة SEO الإضافية ──
            vendor_idx = self._find_column(headers, ['Vendor', 'vendor'])
            body_idx = self._find_column(headers, ['Body (HTML)', 'body (html)', 'Body', 'body'])
            type_idx = self._find_column(headers, ['Type', 'type'])
            tags_idx = self._find_column(headers, ['Tags', 'tags'])
            option1_val_idx = self._find_column(headers, ['Option1 Value', 'option1 value'])
            olfactory_idx = self._find_column(headers, [
                'Olfactory family (product.metafields.shopify.olfactory-family)',
                'olfactory family', 'Olfactory family'
            ])
            scent_idx = self._find_column(headers, [
                'Scent (product.metafields.shopify.scent)',
                'scent', 'Scent'
            ])
            season_idx = self._find_column(headers, [
                'Season (product.metafields.shopify.season)',
                'season', 'Season'
            ])
            gender_idx = self._find_column(headers, [
                'Target gender (product.metafields.shopify.target-gender)',
                'target gender', 'Target gender'
            ])
            fragrance_idx = self._find_column(headers, [
                'Fragrance (product.metafields.shopify.fragrance)',
                'fragrance', 'Fragrance'
            ])

            if handle_idx == -1:
                print(f"{Colors.RED}❌ لم يتم العثور على عمود 'Handle' في الملف{Colors.RESET}")
                print(f"   الأعمدة الموجودة: {headers}")
                sys.exit(1)

            if image_src_idx == -1:
                print(f"{Colors.RED}❌ لم يتم العثور على عمود 'Image Src' في الملف{Colors.RESET}")
                print(f"   الأعمدة الموجودة: {headers}")
                sys.exit(1)

            print(f"{Colors.GREEN}✅ تم اكتشاف أعمدة الملف بنجاح{Colors.RESET}")
            if title_idx != -1:
                print(f"   📋 Handle (عمود {handle_idx+1}), Title (عمود {title_idx+1}), Image Src (عمود {image_src_idx+1})")
            else:
                print(f"   📋 Handle (عمود {handle_idx+1}), Image Src (عمود {image_src_idx+1})")

            # عرض أعمدة SEO المكتشفة
            seo_cols = []
            if vendor_idx != -1: seo_cols.append('Vendor')
            if body_idx != -1: seo_cols.append('Body')
            if olfactory_idx != -1: seo_cols.append('Olfactory')
            if scent_idx != -1: seo_cols.append('Scent')
            if season_idx != -1: seo_cols.append('Season')
            if gender_idx != -1: seo_cols.append('Gender')
            if seo_cols:
                print(f"   🔍 أعمدة SEO: {', '.join(seo_cols)}")

            current_title = ""
            current_vendor = ""
            current_body = ""
            current_type = ""
            current_tags = ""
            current_olfactory = ""
            current_scent = ""
            current_season = ""
            current_gender = ""
            current_fragrance = ""
            current_sizes = []
            row_count = 0

            for row in reader:
                row_count += 1
                if len(row) <= max(handle_idx, image_src_idx):
                    continue

                handle = row[handle_idx].strip()
                if not handle:
                    continue

                # البيانات تظهر فقط في الصف الأول للمنتج
                if title_idx != -1 and title_idx < len(row) and row[title_idx].strip():
                    current_title = row[title_idx].strip()
                    # استخراج بيانات SEO من الصف الأول
                    current_vendor = self._safe_get(row, vendor_idx)
                    current_body = self._safe_get(row, body_idx)
                    current_type = self._safe_get(row, type_idx)
                    current_tags = self._safe_get(row, tags_idx)
                    current_olfactory = self._safe_get(row, olfactory_idx)
                    current_scent = self._safe_get(row, scent_idx)
                    current_season = self._safe_get(row, season_idx)
                    current_gender = self._safe_get(row, gender_idx)
                    current_fragrance = self._safe_get(row, fragrance_idx)
                    current_sizes = []

                # جمع المقاسات من Option1 Value
                opt_val = self._safe_get(row, option1_val_idx)
                if opt_val and opt_val not in current_sizes and handle in self.products:
                    current_sizes.append(opt_val)
                elif opt_val and opt_val not in current_sizes:
                    current_sizes.append(opt_val)

                # إنشاء سجل المنتج إذا لم يكن موجودًا
                if handle not in self.products:
                    self.products[handle] = {
                        'title': current_title,
                        'vendor': current_vendor,
                        'body_html': current_body,
                        'type': current_type,
                        'tags': current_tags,
                        'olfactory_family': current_olfactory,
                        'scent': current_scent,
                        'season': current_season,
                        'target_gender': current_gender,
                        'fragrance': current_fragrance,
                        'sizes': current_sizes,
                        'images': []  # list of {'url': ..., 'position': ...}
                    }

                # تحديث المقاسات
                if opt_val and opt_val not in self.products[handle].get('sizes', []):
                    self.products[handle].setdefault('sizes', []).append(opt_val)

                # استخراج position
                position = self._safe_get(row, img_position_idx, '0')
                try:
                    position = int(position)
                except ValueError:
                    position = 0

                # جمع صورة المنتج الرئيسية
                if image_src_idx < len(row) and row[image_src_idx].strip():
                    img_url = row[image_src_idx].strip()
                    # التأكد من عدم التكرار
                    existing_urls = [img['url'] for img in self.products[handle]['images']]
                    if img_url.startswith('http') and img_url not in existing_urls:
                        img_position = position if position > 0 else len(self.products[handle]['images']) + 1
                        self.products[handle]['images'].append({
                            'url': img_url,
                            'position': img_position,
                        })

                # جمع صورة الـ Variant إن وجدت (ومختلفة عن الرئيسية)
                if variant_img_idx != -1 and variant_img_idx < len(row) and row[variant_img_idx].strip():
                    var_url = row[variant_img_idx].strip()
                    existing_urls = [img['url'] for img in self.products[handle]['images']]
                    if var_url.startswith('http') and var_url not in existing_urls:
                        self.products[handle]['images'].append({
                            'url': var_url,
                            'position': len(self.products[handle]['images']) + 1,
                        })

        # إحصائيات
        total_images = sum(len(p['images']) for p in self.products.values())
        print(f"\n{Colors.CYAN}📊 ملخص الملف:{Colors.RESET}")
        print(f"   📦 عدد المنتجات: {Colors.BOLD}{len(self.products)}{Colors.RESET}")
        print(f"   🖼️  عدد الصور: {Colors.BOLD}{total_images}{Colors.RESET}")
        print(f"   📄 عدد الصفوف: {Colors.BOLD}{row_count}{Colors.RESET}")

        return self.products


# ─────────────────────────────────────────────
# 2. تحميل الصور
# ─────────────────────────────────────────────
class ImageDownloader:
    """تحميل الصور بشكل متوازي مع إعادة المحاولة."""

    def __init__(self, output_dir: str = "downloaded_images", workers: int = 10, max_retries: int = 3):
        self.output_dir = output_dir
        self.workers = workers
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.logger = logging.getLogger("Downloader")
        self.stats = {'success': 0, 'failed': 0, 'skipped': 0, 'total_size': 0}
        self.failed_downloads = []

    def _get_extension(self, url: str) -> str:
        """استخراج امتداد الصورة من الرابط."""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        # إزالة query parameters من الامتداد
        ext = os.path.splitext(path)[1].split('?')[0].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg']:
            return ext
        return '.jpg'  # افتراضي

    def _download_single(self, url: str, save_path: str, handle: str) -> dict:
        """تحميل صورة واحدة مع إعادة المحاولة."""
        # تخطي الصور المحملة مسبقًا (دعم الاستكمال)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            size = os.path.getsize(save_path)
            return {'status': 'skipped', 'path': save_path, 'size': size, 'handle': handle}

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=30, stream=True)
                response.raise_for_status()

                # التأكد من أن المحتوى صورة
                content_type = response.headers.get('content-type', '')
                if 'image' not in content_type and 'octet-stream' not in content_type:
                    self.logger.warning(f"المحتوى ليس صورة: {content_type} - {url}")

                # حفظ الصورة
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                size = os.path.getsize(save_path)
                return {'status': 'success', 'path': save_path, 'size': size, 'handle': handle}

            except Exception as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"فشل تحميل {url} بعد {self.max_retries} محاولات: {e}")
                    return {'status': 'failed', 'url': url, 'error': str(e), 'handle': handle}

    def download_all(self, products: dict) -> dict:
        """تحميل جميع صور المنتجات بشكل متوازي."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}📥 بدء تحميل الصور...{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        # إنشاء قائمة مهام التحميل
        download_tasks = []
        for handle, product in products.items():
            product_dir = os.path.join(self.output_dir, self._sanitize_dirname(handle))
            title = product.get('title', '') or handle
            safe_title = self._sanitize_filename(title)
            total_imgs = len(product['images'])
            for idx, img_data in enumerate(product['images'], 1):
                # دعم الصيغة الجديدة (dict) والقديمة (string)
                if isinstance(img_data, dict):
                    url = img_data['url']
                    position = img_data.get('position', idx)
                else:
                    url = img_data
                    position = idx
                ext = self._get_extension(url)
                if total_imgs == 1:
                    filename = f"{safe_title}{ext}"
                else:
                    filename = f"{safe_title}-{position}{ext}"
                save_path = os.path.join(product_dir, filename)
                download_tasks.append((url, save_path, handle))

        if not download_tasks:
            print(f"{Colors.YELLOW}⚠️ لا توجد صور للتحميل{Colors.RESET}")
            return self.stats

        # تحميل متوازي مع شريط تقدم
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._download_single, url, path, handle): (url, handle)
                for url, path, handle in download_tasks
            }

            with tqdm(total=len(futures), desc="⬇️  تحميل الصور", unit="صورة",
                       bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    if result['status'] == 'success':
                        self.stats['success'] += 1
                        self.stats['total_size'] += result['size']
                    elif result['status'] == 'skipped':
                        self.stats['skipped'] += 1
                        self.stats['total_size'] += result['size']
                    else:
                        self.stats['failed'] += 1
                        self.failed_downloads.append(result)
                    pbar.update(1)

        # ملخص التحميل
        print(f"\n{Colors.GREEN}✅ اكتمل التحميل:{Colors.RESET}")
        print(f"   ✓ نجح: {Colors.GREEN}{self.stats['success']}{Colors.RESET}")
        if self.stats['skipped'] > 0:
            print(f"   ⏭️ تم تخطيه (موجود مسبقًا): {Colors.YELLOW}{self.stats['skipped']}{Colors.RESET}")
        if self.stats['failed'] > 0:
            print(f"   ✗ فشل: {Colors.RED}{self.stats['failed']}{Colors.RESET}")
        print(f"   📦 الحجم الكلي: {self._format_size(self.stats['total_size'])}")

        return self.stats

    def _sanitize_dirname(self, name: str) -> str:
        """تنظيف اسم المجلد من الأحرف غير المسموحة."""
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = sanitized.strip('. ')
        return sanitized if sanitized else 'unknown_product'

    def _sanitize_filename(self, name: str) -> str:
        """
        تنظيف اسم الملف من الأحرف غير المسموحة.
        يحوّل المسافات لشرطات ويزيل أي رمز غير مسموح به في أسماء الملفات.
        """
        # إزالة الأحرف غير المسموحة في Windows
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        # استبدال المسافات والأحرف الخاصة الأخرى بشرطة
        sanitized = re.sub(r'[\s]+', '-', sanitized)
        # إزالة الشرطات المتكررة
        sanitized = re.sub(r'-{2,}', '-', sanitized)
        sanitized = sanitized.strip('-. ')
        return sanitized if sanitized else 'product'

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """تحويل الحجم من بايت إلى صيغة مقروءة."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# ─────────────────────────────────────────────
# 3. ضغط وتحسين الصور — محسّن لـ SEO
# ─────────────────────────────────────────────
class ImageCompressor:
    """ضغط الصور وتحويلها لـ WebP مع تحسين SEO (أسماء + alt text + حجم 80-150KB)."""

    # الحد الأقصى والأدنى لحجم الملف المستهدف
    TARGET_MAX_SIZE = 150 * 1024   # 150 KB
    TARGET_MIN_SIZE = 80 * 1024    # 80 KB
    MAX_DIMENSION = 2000           # أقصى بُعد 2000px

    def __init__(self, input_dir: str = "downloaded_images",
                 output_dir: str = "compressed_images", quality: int = 85):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.quality = quality
        self.logger = logging.getLogger("Compressor")
        self.stats = {
            'processed': 0, 'failed': 0,
            'original_size': 0, 'compressed_size': 0,
            'converted_webp': 0,
            'videos_processed': 0, 'videos_failed': 0,
            'videos_original_size': 0, 'videos_compressed_size': 0,
            'thumbnails_generated': 0,
        }
        # خريطة SEO: handle → [{position, old_name, new_name, alt_text}]
        self.seo_map = {}

    def compress_all(self) -> dict:
        """ضغط جميع الصور المحملة (الطريقة القديمة بدون SEO)."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}🗜️  تحويل الصور لـ WebP وضغطها...{Colors.RESET}")
        print(f"   جودة: {self.quality}% | حجم مستهدف: 80-150 KB | أقصى بُعد: 2000px")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        if not os.path.exists(self.input_dir):
            print(f"{Colors.RED}❌ مجلد الصور غير موجود: {self.input_dir}{Colors.RESET}")
            return self.stats

        image_files = []
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif')):
                    image_files.append(os.path.join(root, file))

        if not image_files:
            print(f"{Colors.YELLOW}⚠️ لا توجد صور للضغط{Colors.RESET}")
            return self.stats

        with tqdm(total=len(image_files), desc="🗜️  ضغط + WebP", unit="صورة",
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            for img_path in image_files:
                try:
                    self._compress_single_legacy(img_path)
                except Exception as e:
                    self.stats['failed'] += 1
                    self.logger.error(f"فشل ضغط {img_path}: {e}")
                pbar.update(1)

        self._print_summary()
        return self.stats

    def compress_all_seo(self, products: dict, seo_logger=None, progress_callback=None) -> dict:
        """
        ضغط جميع الصور مع تحسين SEO كامل.
        - أسماء ملفات SEO-friendly
        - توليد alt text ديناميكي
        - ضغط لـ 80-150 KB
        - Resize لو > 2000x2000
        """
        if not SEO_AVAILABLE:
            print(f"{Colors.YELLOW}⚠️ seo_helpers.py غير موجود، استخدام الضغط العادي{Colors.RESET}")
            return self.compress_all()

        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}🗜️  ضغط + تحسين SEO للصور...{Colors.RESET}")
        print(f"   حجم مستهدف: 80-150 KB | أقصى بُعد: 2000px | صيغة: WebP")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        if not os.path.exists(self.input_dir):
            print(f"{Colors.RED}❌ مجلد الصور غير موجود: {self.input_dir}{Colors.RESET}")
            return self.stats

        # بناء قائمة المهام من بيانات المنتجات
        tasks = []
        for handle, product in products.items():
            handle_dir = re.sub(r'[<>:"/\\|?*]', '_', handle).strip('. ') or 'unknown_product'
            src_dir = os.path.join(self.input_dir, handle_dir)

            if not os.path.exists(src_dir):
                continue

            # جمع الصور الموجودة فعلياً في المجلد
            existing_files = sorted([
                f for f in os.listdir(src_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'))
            ])

            # جمع الفيديوهات الموجودة في المجلد
            existing_videos = []
            if VIDEO_AVAILABLE:
                existing_videos = sorted([
                    f for f in os.listdir(src_dir)
                    if f.lower().endswith(VIDEO_EXTENSIONS)
                ])

            if not existing_files and not existing_videos:
                continue

            # استخراج بيانات SEO
            title = product.get('title', '') or handle
            vendor = product.get('vendor', '') or ''
            slug = build_unique_slug(handle, title)
            brand, perfume = extract_brand_and_perfume(handle, title, vendor)
            total_imgs = len(existing_files)

            # بناء metadata لـ alt text
            sizes_list = product.get('sizes', [])
            clean_sizes = [
                s for s in sizes_list
                if s and s.lower() not in ('default title', 'default', 'title', '')
                and not s.lower().startswith('default')
            ]
            sizes_str = ', '.join(clean_sizes) if clean_sizes else ''
            notes_snippet = _extract_notes_snippet(product.get('body_html', '')) if SEO_AVAILABLE else ''

            metadata = {
                'olfactory_family': product.get('olfactory_family', ''),
                'scent': product.get('scent', ''),
                'season': product.get('season', ''),
                'target_gender': product.get('target_gender', ''),
                'sizes': sizes_str,
                'notes_snippet': notes_snippet,
            }

            for idx, filename in enumerate(existing_files):
                position = idx + 1
                src_path = os.path.join(src_dir, filename)
                seo_filename = generate_seo_filename(slug, position, total_imgs)
                dst_dir = os.path.join(self.output_dir, handle_dir)
                os.makedirs(dst_dir, exist_ok=True)
                dst_path = os.path.join(dst_dir, seo_filename)
                alt_text = generate_alt_text(brand, perfume, position, total_imgs, metadata)

                tasks.append({
                    'handle': handle, 'position': position, 'src_path': src_path,
                    'dst_path': dst_path, 'old_name': filename, 'new_name': seo_filename,
                    'alt_text': alt_text, 'type': 'image'
                })

            # ── مهام الفيديو ──
            for vidx, vfilename in enumerate(existing_videos):
                vid_position = vidx + 1
                vid_src_path = os.path.join(src_dir, vfilename)
                vid_seo_filename = generate_video_seo_filename(slug, vid_position, len(existing_videos))
                vid_dst_dir = os.path.join(self.output_dir, handle_dir)
                os.makedirs(vid_dst_dir, exist_ok=True)
                vid_dst_path = os.path.join(vid_dst_dir, vid_seo_filename)
                vid_alt_text = generate_video_alt_text(brand, perfume, vid_position, len(existing_videos), metadata)
                # اسم Thumbnail
                thumb_filename = generate_video_thumbnail_filename(slug, vid_position)
                thumb_path = os.path.join(vid_dst_dir, thumb_filename)

                tasks.append({
                    'handle': handle,
                    'position': vid_position,
                    'src_path': vid_src_path,
                    'dst_path': vid_dst_path,
                    'old_name': vfilename,
                    'new_name': vid_seo_filename,
                    'alt_text': vid_alt_text,
                    'type': 'video',
                    'thumb_path': thumb_path,
                    'thumb_filename': thumb_filename,
                })

        if not tasks:
            print(f"{Colors.YELLOW}⚠️ لا توجد صور أو فيديوهات للضغط{Colors.RESET}")
            return self.stats

        # تنفيذ الضغط
        with tqdm(total=len(tasks), desc="🗜️  SEO ضغط", unit="صورة",
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            for task in tasks:
                try:
                    comp_stats = compress_image_seo(
                        task['src_path'], task['dst_path'],
                        target_min_kb=80, target_max_kb=150,
                        max_dimension=self.MAX_DIMENSION
                    )

                    self.stats['original_size'] += comp_stats['original_size']
                    self.stats['compressed_size'] += comp_stats['compressed_size']
                    self.stats['processed'] += 1
                    self.stats['converted_webp'] += 1

                    # حفظ في خريطة SEO
                    handle = task['handle']
                    if handle not in self.seo_map:
                        self.seo_map[handle] = []
                    self.seo_map[handle].append({
                        'position': task['position'],
                        'old_name': task['old_name'],
                        'new_name': task['new_name'],
                        'alt_text': task['alt_text'],
                    })

                    # تسجيل في SEO Logger
                    if seo_logger:
                        seo_logger.add_entry(
                            handle=handle,
                            position=task['position'],
                            old_filename=task['old_name'],
                            new_filename=task['new_name'],
                            alt_text=task['alt_text'],
                            compress_stats=comp_stats,
                        )

                except Exception as e:
                    self.stats['failed'] += 1
                    self.logger.error(f"فشل ضغط {task['src_path']}: {e}")

                pbar.update(1)
                if progress_callback:
                    # Check if GUI requested a stop by making the callback return False
                    if progress_callback(self.stats['processed'], len(tasks)) is False:
                        break

        self._print_summary()
        return self.stats

    def _print_summary(self):
        """طباعة ملخص الضغط."""
        if self.stats['original_size'] > 0:
            savings = self.stats['original_size'] - self.stats['compressed_size']
            savings_pct = (savings / self.stats['original_size']) * 100

            print(f"\n{Colors.GREEN}✅ اكتمل الضغط:{Colors.RESET}")
            print(f"   ✓ تم ضغط: {Colors.GREEN}{self.stats['processed']}{Colors.RESET} صورة")
            print(f"   ✓ تم تحويل لـ WebP: {Colors.CYAN}{self.stats['converted_webp']}{Colors.RESET}")
            if self.stats['failed'] > 0:
                print(f"   ✗ فشل: {Colors.RED}{self.stats['failed']}{Colors.RESET}")
            print(f"   📦 الحجم الأصلي:  {ImageDownloader._format_size(self.stats['original_size'])}")
            print(f"   📦 بعد الضغط:     {ImageDownloader._format_size(self.stats['compressed_size'])}")
            print(f"   💰 التوفير:       {Colors.GREEN}{Colors.BOLD}{ImageDownloader._format_size(savings)} ({savings_pct:.1f}%){Colors.RESET}")

    def _compress_single_legacy(self, img_path: str):
        """ضغط صورة واحدة (الطريقة القديمة): تحويل WebP مع استهداف 80-150KB."""
        rel_path = os.path.relpath(img_path, self.input_dir)
        output_path = os.path.join(self.output_dir, rel_path)
        output_path = os.path.splitext(output_path)[0] + '.webp'

        if SEO_AVAILABLE:
            comp_stats = compress_image_seo(
                img_path, output_path,
                target_min_kb=80, target_max_kb=150,
                max_dimension=self.MAX_DIMENSION
            )
            self.stats['original_size'] += comp_stats['original_size']
            self.stats['compressed_size'] += comp_stats['compressed_size']
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            original_size = os.path.getsize(img_path)
            self.stats['original_size'] += original_size
            with Image.open(img_path) as img:
                # تصحيح اتجاه الصورة بناءً على EXIF Orientation tag
                img = ImageOps.exif_transpose(img)
                if img.mode == 'RGBA':
                    alpha = img.getchannel('A')
                    if alpha.getextrema() == (255, 255):
                        img = img.convert('RGB')
                elif img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                # Resize if > 2000
                w, h = img.size
                if w > self.MAX_DIMENSION or h > self.MAX_DIMENSION:
                    ratio = min(self.MAX_DIMENSION / w, self.MAX_DIMENSION / h)
                    img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                img.save(output_path, 'WEBP', quality=self.quality, method=4, optimize=True)
                file_size = os.path.getsize(output_path)
                if file_size > self.TARGET_MAX_SIZE:
                    for lower_q in range(self.quality - 10, 25, -10):
                        img.save(output_path, 'WEBP', quality=lower_q, method=4, optimize=True)
                        if os.path.getsize(output_path) <= self.TARGET_MAX_SIZE:
                            break
            self.stats['compressed_size'] += os.path.getsize(output_path)

        self.stats['processed'] += 1
        self.stats['converted_webp'] += 1


# ─────────────────────────────────────────────
# 3.5 تصدير CSV محسّن لشوبيفاي
# ─────────────────────────────────────────────
class ShopifyCSVExporter:
    """
    تصدير CSV محسّن لشوبيفاي مع أسماء ملفات SEO و Alt Text.
    يقرأ الملف الأصلي ويحدّث أعمدة Image Src و Image Alt Text
    مع الحفاظ على كل الأعمدة الأخرى.
    """

    def __init__(self, original_csv: str, seo_map: dict, output_path: str = None):
        """
        Args:
            original_csv: مسار ملف CSV الأصلي
            seo_map: خريطة SEO من ImageCompressor
                     {handle: [{position, old_name, new_name, alt_text}]}
            output_path: مسار ملف CSV الناتج
        """
        self.original_csv = original_csv
        self.seo_map = seo_map
        if output_path:
            self.output_path = output_path
        else:
            base = os.path.splitext(original_csv)[0]
            self.output_path = f"{base}_seo_optimized.csv"
        self.logger = logging.getLogger("CSVExporter")

    def export(self) -> str:
        """تصدير الملف المحسّن."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}📄 تصدير CSV محسّن لشوبيفاي...{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        # بناء lookup: (handle, position) → {new_name, alt_text}
        lookup = {}
        for handle, entries in self.seo_map.items():
            for entry in entries:
                key = (handle, entry['position'])
                lookup[key] = entry

        # اكتشاف الترميز
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1256']
        encoding = 'utf-8'
        for enc in encodings:
            try:
                with open(self.original_csv, 'r', encoding=enc) as f:
                    f.read(1024)
                encoding = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        # قراءة وتعديل
        rows_modified = 0
        with open(self.original_csv, 'r', encoding=encoding, newline='') as fin:
            reader = csv.reader(fin)
            headers = next(reader)

            # البحث عن أعمدة
            headers_lower = [h.strip().lower() for h in headers]
            handle_idx = headers_lower.index('handle') if 'handle' in headers_lower else -1
            img_src_idx = headers_lower.index('image src') if 'image src' in headers_lower else -1
            img_pos_idx = headers_lower.index('image position') if 'image position' in headers_lower else -1

            # البحث عن أو إضافة عمود Image Alt Text
            alt_idx = -1
            for i, h in enumerate(headers_lower):
                if 'image alt' in h:
                    alt_idx = i
                    break

            if alt_idx == -1:
                # إضافة عمود جديد بعد Image Position أو Image Src
                insert_after = img_pos_idx if img_pos_idx != -1 else img_src_idx
                if insert_after != -1:
                    alt_idx = insert_after + 1
                    headers.insert(alt_idx, 'Image Alt Text')
                else:
                    headers.append('Image Alt Text')
                    alt_idx = len(headers) - 1

            if handle_idx == -1 or img_src_idx == -1:
                print(f"{Colors.RED}❌ لم يتم العثور على أعمدة Handle/Image Src{Colors.RESET}")
                return ''

            # position tracker per handle
            handle_positions = {}

            all_rows = [headers]
            for row in reader:
                # التأكد من أن الصف بنفس طول الهيدر
                while len(row) < len(headers):
                    row.append('')
                if len(row) > len(headers):
                    row = row[:len(headers)]

                if len(row) <= max(handle_idx, img_src_idx):
                    all_rows.append(row)
                    continue

                handle = row[handle_idx].strip()
                img_src = row[img_src_idx].strip() if img_src_idx < len(row) else ''

                if handle and img_src:
                    # تحديد الـ position
                    if img_pos_idx != -1 and img_pos_idx < len(row) and row[img_pos_idx].strip():
                        try:
                            pos = int(row[img_pos_idx].strip())
                        except ValueError:
                            pos = handle_positions.get(handle, 0) + 1
                    else:
                        pos = handle_positions.get(handle, 0) + 1

                    handle_positions[handle] = max(handle_positions.get(handle, 0), pos)

                    key = (handle, pos)
                    if key in lookup:
                        entry = lookup[key]
                        # تحديث Image Src باسم الملف الجديد
                        row[img_src_idx] = entry['new_name']
                        # تحديث Image Alt Text
                        row[alt_idx] = entry['alt_text']
                        rows_modified += 1

                all_rows.append(row)

        # كتابة الملف الناتج
        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as fout:
            writer = csv.writer(fout)
            writer.writerows(all_rows)

        print(f"{Colors.GREEN}✅ تم تصدير CSV محسّن:{Colors.RESET}")
        print(f"   📄 الملف: {Colors.BOLD}{self.output_path}{Colors.RESET}")
        print(f"   ✏️  صفوف معدّلة: {Colors.CYAN}{rows_modified}{Colors.RESET}")
        print(f"   📊 أعمدة محدّثة: Image Src, Image Alt Text")

        return self.output_path


# ─────────────────────────────────────────────
# 4. رفع الصور إلى شوبيفاي عبر API
# ─────────────────────────────────────────────
class ShopifyUploader:
    """رفع الصور المضغوطة إلى متجر شوبيفاي عبر Admin API."""

    # شوبيفاي يسمح بـ 2 طلب/ثانية - نستخدم 0.6 ثانية بين الطلبات للأمان
    RATE_LIMIT_DELAY = 0.6
    API_VERSION = "2024-01"

    def __init__(self, shop_domain: str, access_token: str, compressed_dir: str = "compressed_images"):
        # تنظيف اسم المتجر
        self.shop_domain = shop_domain.replace("https://", "").replace("http://", "").rstrip("/")
        if not self.shop_domain.endswith(".myshopify.com"):
            self.shop_domain += ".myshopify.com"

        self.access_token = access_token
        self.compressed_dir = compressed_dir
        self.base_url = f"https://{self.shop_domain}/admin/api/{self.API_VERSION}"
        self.session = requests.Session()
        self.session.headers.update({
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        })
        self.logger = logging.getLogger("Uploader")
        self.stats = {'uploaded': 0, 'failed': 0, 'products_updated': 0}

    def _api_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """إرسال طلب لـ Shopify API مع احترام حد الطلبات."""
        url = f"{self.base_url}/{endpoint}"
        time.sleep(self.RATE_LIMIT_DELAY)

        try:
            if method == 'GET':
                resp = self.session.get(url, timeout=30)
            elif method == 'POST':
                resp = self.session.post(url, json=data, timeout=60)
            elif method == 'DELETE':
                resp = self.session.delete(url, timeout=30)
            elif method == 'PUT':
                resp = self.session.put(url, json=data, timeout=60)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # التحقق من حد الطلبات
            if resp.status_code == 429:
                retry_after = float(resp.headers.get('Retry-After', 2))
                self.logger.warning(f"⏳ تم الوصول لحد الطلبات، انتظار {retry_after} ثانية...")
                time.sleep(retry_after)
                return self._api_request(method, endpoint, data)

            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"خطأ API: {e} - {resp.text if resp else 'No response'}")
            raise
        except Exception as e:
            self.logger.error(f"خطأ اتصال: {e}")
            raise

    def test_connection(self) -> bool:
        """اختبار الاتصال بالمتجر."""
        print(f"\n{Colors.CYAN}🔗 اختبار الاتصال بمتجر: {self.shop_domain}...{Colors.RESET}")
        try:
            result = self._api_request('GET', 'shop.json')
            shop_name = result.get('shop', {}).get('name', 'Unknown')
            print(f"{Colors.GREEN}✅ تم الاتصال بنجاح! المتجر: {shop_name}{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.RED}❌ فشل الاتصال: {e}{Colors.RESET}")
            print(f"{Colors.YELLOW}   تأكد من صحة اسم المتجر و Access Token{Colors.RESET}")
            return False

    def _get_product_by_handle(self, handle: str) -> dict:
        """البحث عن منتج بالـ Handle."""
        try:
            result = self._api_request('GET', f'products.json?handle={handle}&fields=id,handle,title,images')
            products = result.get('products', [])
            if products:
                return products[0]
            return None
        except Exception:
            return None

    def _delete_product_images(self, product_id: int, images: list):
        """حذف صور المنتج القديمة."""
        for img in images:
            try:
                self._api_request('DELETE', f'products/{product_id}/images/{img["id"]}.json')
            except Exception as e:
                self.logger.warning(f"فشل حذف صورة {img['id']}: {e}")

    def _upload_image(self, product_id: int, image_path: str, position: int) -> bool:
        """رفع صورة واحدة لمنتج."""
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # تحديد نوع الصورة
            ext = os.path.splitext(image_path)[1].lower()
            filename = os.path.basename(image_path)

            data = {
                "image": {
                    "position": position,
                    "attachment": image_data,
                    "filename": filename
                }
            }

            self._api_request('POST', f'products/{product_id}/images.json', data)
            return True

        except Exception as e:
            self.logger.error(f"فشل رفع {image_path}: {e}")
            return False

    def upload_all(self, products: dict, dry_run: bool = False) -> dict:
        """رفع جميع الصور المضغوطة."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        if dry_run:
            print(f"{Colors.BOLD}🔍 وضع المعاينة (Dry Run) - لن يتم رفع أي شيء{Colors.RESET}")
        else:
            print(f"{Colors.BOLD}☁️  بدء رفع الصور إلى شوبيفاي...{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        # اختبار الاتصال أولًا
        if not self.test_connection():
            return self.stats

        # تجميع المنتجات التي لها صور مضغوطة
        upload_tasks = []
        for handle in products:
            sanitized = re.sub(r'[<>:"/\\|?*]', '_', handle).strip('. ') or 'unknown_product'
            product_dir = os.path.join(self.compressed_dir, sanitized)
            if os.path.exists(product_dir):
                images = sorted([
                    os.path.join(product_dir, f)
                    for f in os.listdir(product_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
                ])
                if images:
                    upload_tasks.append({'handle': handle, 'images': images})

        if not upload_tasks:
            print(f"{Colors.YELLOW}⚠️ لا توجد صور مضغوطة للرفع{Colors.RESET}")
            return self.stats

        print(f"   📦 منتجات للرفع: {len(upload_tasks)}")
        total_images = sum(len(t['images']) for t in upload_tasks)
        print(f"   🖼️  صور للرفع: {total_images}")

        if dry_run:
            print(f"\n{Colors.YELLOW}📋 تفاصيل المعاينة:{Colors.RESET}")
            for task in upload_tasks:
                title = products[task['handle']].get('title', task['handle'])
                print(f"   📦 {title} ({task['handle']}) → {len(task['images'])} صور")
            print(f"\n{Colors.CYAN}💡 لتنفيذ الرفع فعليًا، أزل --dry-run{Colors.RESET}")
            return self.stats

        # تأكيد قبل الرفع
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  تنبيه: سيتم حذف الصور القديمة واستبدالها بالمضغوطة!{Colors.RESET}")
        confirm = input(f"{Colors.YELLOW}   هل تريد المتابعة؟ (نعم/yes/y): {Colors.RESET}").strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print(f"{Colors.CYAN}🚫 تم إلغاء الرفع{Colors.RESET}")
            return self.stats

        # بدء الرفع
        with tqdm(total=len(upload_tasks), desc="☁️  رفع المنتجات", unit="منتج",
                   bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            for task in upload_tasks:
                handle = task['handle']
                title = products[handle].get('title', handle)

                # البحث عن المنتج في شوبيفاي
                product = self._get_product_by_handle(handle)
                if not product:
                    self.logger.warning(f"المنتج غير موجود في المتجر: {handle}")
                    self.stats['failed'] += len(task['images'])
                    pbar.update(1)
                    continue

                product_id = product['id']

                # حذف الصور القديمة
                old_images = product.get('images', [])
                if old_images:
                    self._delete_product_images(product_id, old_images)

                # رفع الصور الجديدة
                all_success = True
                for idx, img_path in enumerate(task['images'], 1):
                    if self._upload_image(product_id, img_path, idx):
                        self.stats['uploaded'] += 1
                    else:
                        self.stats['failed'] += 1
                        all_success = False

                if all_success:
                    self.stats['products_updated'] += 1

                pbar.update(1)

        # ملخص الرفع
        print(f"\n{Colors.GREEN}✅ اكتمل الرفع:{Colors.RESET}")
        print(f"   ✓ منتجات محدّثة: {Colors.GREEN}{self.stats['products_updated']}{Colors.RESET}")
        print(f"   ✓ صور مرفوعة: {Colors.GREEN}{self.stats['uploaded']}{Colors.RESET}")
        if self.stats['failed'] > 0:
            print(f"   ✗ فشل: {Colors.RED}{self.stats['failed']}{Colors.RESET}")

        return self.stats


# ─────────────────────────────────────────────
# 5. إنشاء التقرير
# ─────────────────────────────────────────────
class ReportGenerator:
    """إنشاء تقرير شامل بنتائج العملية."""

    def __init__(self, output_path: str = "report.txt"):
        self.output_path = output_path

    def generate(self, products: dict, download_stats: dict,
                 compress_stats: dict, upload_stats: dict = None):
        """إنشاء التقرير النهائي."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_images = sum(len(p['images']) for p in products.values())

        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║          تقرير أداة صور شوبيفاي بالجملة                ║",
            "║          Shopify Bulk Image Tool Report                 ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
            f"📅 التاريخ: {timestamp}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 إحصائيات عامة",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  📦 عدد المنتجات: {len(products)}",
            f"  🖼️  إجمالي الصور: {total_images}",
            "",
        ]

        if download_stats:
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "📥 التحميل",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"  ✅ نجح: {download_stats.get('success', 0)}",
                f"  ⏭️  تخطي: {download_stats.get('skipped', 0)}",
                f"  ❌ فشل: {download_stats.get('failed', 0)}",
                f"  📦 الحجم الكلي: {ImageDownloader._format_size(download_stats.get('total_size', 0))}",
                "",
            ])

        if compress_stats and compress_stats.get('processed', 0) > 0:
            original = compress_stats.get('original_size', 0)
            compressed = compress_stats.get('compressed_size', 0)
            savings = original - compressed
            savings_pct = (savings / original * 100) if original > 0 else 0

            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "🗜️  الضغط",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"  ✅ تم ضغط: {compress_stats.get('processed', 0)}",
                f"  ❌ فشل: {compress_stats.get('failed', 0)}",
                f"  📦 الحجم الأصلي: {ImageDownloader._format_size(original)}",
                f"  📦 بعد الضغط: {ImageDownloader._format_size(compressed)}",
                f"  💰 التوفير: {ImageDownloader._format_size(savings)} ({savings_pct:.1f}%)",
                "",
            ])

        if upload_stats and (upload_stats.get('uploaded', 0) > 0 or upload_stats.get('failed', 0) > 0):
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "☁️  الرفع إلى شوبيفاي",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"  ✅ منتجات محدثة: {upload_stats.get('products_updated', 0)}",
                f"  ✅ صور مرفوعة: {upload_stats.get('uploaded', 0)}",
                f"  ❌ فشل: {upload_stats.get('failed', 0)}",
                "",
            ])

        # تفاصيل المنتجات
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 تفاصيل المنتجات",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ])

        for handle, product in products.items():
            title = product.get('title', handle)
            img_count = len(product['images'])
            lines.append(f"  📦 {title} ({handle}) - {img_count} صور")

        lines.extend(["", "═══════════════════════════════════════════", ""])

        report_content = "\n".join(lines)

        # حفظ التقرير
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"\n{Colors.GREEN}📊 تم حفظ التقرير: {Colors.BOLD}{self.output_path}{Colors.RESET}")

        return report_content


# ─────────────────────────────────────────────
# 6. واجهة سطر الأوامر (CLI)
# ─────────────────────────────────────────────
def setup_logging(log_file: str = "shopify_images.log"):
    """إعداد نظام السجلات."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )


def parse_arguments():
    """تحليل وسائط سطر الأوامر."""
    parser = argparse.ArgumentParser(
        description="🛒 أداة تحميل وضغط ورفع صور منتجات شوبيفاي بالجملة",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة الاستخدام:
  %(prog)s products.csv                                     # تحميل + ضغط
  %(prog)s products.csv --quality 80                        # جودة ضغط مخصصة
  %(prog)s products.csv --workers 20                        # تحميل أسرع
  %(prog)s products.csv --download-only                     # تحميل فقط
  %(prog)s products.csv --compress-only                     # ضغط فقط
  %(prog)s products.csv --upload --shop store --token abc   # تحميل + ضغط + رفع
  %(prog)s products.csv --upload --dry-run --shop s --token t  # معاينة الرفع
        """
    )

    parser.add_argument('csv_file', help='مسار ملف CSV المُصدّر من شوبيفاي')
    parser.add_argument('--quality', type=int, default=85,
                        help='جودة ضغط JPEG (1-100، افتراضي: 85)')
    parser.add_argument('--workers', type=int, default=10,
                        help='عدد خيوط التحميل المتوازي (افتراضي: 10)')
    parser.add_argument('--download-only', action='store_true',
                        help='تحميل فقط بدون ضغط')
    parser.add_argument('--compress-only', action='store_true',
                        help='ضغط الصور المحملة مسبقًا فقط')
    parser.add_argument('--upload', action='store_true',
                        help='رفع الصور المضغوطة إلى شوبيفاي')
    parser.add_argument('--shop', type=str, default='',
                        help='اسم متجر شوبيفاي (مثل: mystore أو mystore.myshopify.com)')
    parser.add_argument('--token', type=str, default='',
                        help='Shopify Admin API Access Token')
    parser.add_argument('--dry-run', action='store_true',
                        help='معاينة ما سيتم رفعه بدون رفع فعلي')
    parser.add_argument('--output-dir', type=str, default='downloaded_images',
                        help='مجلد حفظ الصور المحملة (افتراضي: downloaded_images)')
    parser.add_argument('--compressed-dir', type=str, default='compressed_images',
                        help='مجلد حفظ الصور المضغوطة (افتراضي: compressed_images)')

    return parser.parse_args()


def main():
    """نقطة الدخول الرئيسية."""
    print_banner()
    args = parse_arguments()
    setup_logging()

    start_time = time.time()

    # التحقق من صحة المدخلات
    if args.quality < 1 or args.quality > 100:
        print(f"{Colors.RED}❌ جودة الضغط يجب أن تكون بين 1 و 100{Colors.RESET}")
        sys.exit(1)

    if args.upload and (not args.shop or not args.token):
        print(f"{Colors.RED}❌ للرفع إلى شوبيفاي، يجب تحديد --shop و --token{Colors.RESET}")
        print(f"{Colors.YELLOW}   مثال: --shop mystore.myshopify.com --token shpat_xxxxx{Colors.RESET}")
        sys.exit(1)

    # 1. قراءة ملف CSV
    print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}📄 قراءة ملف CSV...{Colors.RESET}")
    print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

    parser = ShopifyCSVParser(args.csv_file)
    products = parser.parse()

    if not products:
        print(f"{Colors.RED}❌ لم يتم العثور على أي منتجات في الملف{Colors.RESET}")
        sys.exit(1)

    download_stats = {}
    compress_stats = {}
    upload_stats = {}

    # 2. تحميل الصور
    if not args.compress_only:
        downloader = ImageDownloader(
            output_dir=args.output_dir,
            workers=args.workers
        )
        download_stats = downloader.download_all(products)

    # 3. ضغط الصور + تحسين SEO
    if not args.download_only:
        compressor = ImageCompressor(
            input_dir=args.output_dir,
            output_dir=args.compressed_dir,
            quality=args.quality
        )

        if SEO_AVAILABLE:
            # ضغط مع تحسين SEO كامل
            csv_dir = os.path.dirname(os.path.abspath(args.csv_file))
            seo_log_path = os.path.join(csv_dir, 'seo_optimization_log.csv')
            seo_logger = SEOLogger(log_path=seo_log_path)

            compress_stats = compressor.compress_all_seo(products, seo_logger)

            # حفظ SEO log
            seo_logger.save()
            print(f"\n{Colors.GREEN}📋 تم حفظ سجل SEO: {Colors.BOLD}{seo_log_path}{Colors.RESET}")
            print(f"   {seo_logger.get_summary()}")

            # تصدير CSV محسّن
            seo_csv_path = os.path.join(csv_dir, 'products_seo_optimized.csv')
            exporter = ShopifyCSVExporter(
                original_csv=args.csv_file,
                seo_map=compressor.seo_map,
                output_path=seo_csv_path
            )
            exporter.export()
        else:
            compress_stats = compressor.compress_all()

    # 4. رفع إلى شوبيفاي (اختياري)
    if args.upload:
        uploader = ShopifyUploader(
            shop_domain=args.shop,
            access_token=args.token,
            compressed_dir=args.compressed_dir
        )
        upload_stats = uploader.upload_all(products, dry_run=args.dry_run)

    # 5. إنشاء التقرير
    report = ReportGenerator()
    report.generate(products, download_stats, compress_stats, upload_stats)

    # الوقت الكلي
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}🎉 اكتملت العملية بنجاح!{Colors.RESET}")
    print(f"{Colors.CYAN}⏱️  الوقت الكلي: {minutes} دقيقة و {seconds} ثانية{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")


if __name__ == '__main__':
    main()
