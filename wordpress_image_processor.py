#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress/WooCommerce Image Processor — بدون API
معالج صور منتجات ووردبريس: قراءة CSV + ضغط + تسمية SEO + تصدير

هذا الملف مستقل تماماً عن shopify_image_downloader.py.
يستخدم:
  - compress_image_seo() من seo_helpers.py للضغط فقط
  - wordpress_seo_helpers.py للتسمية والـ Alt Text
"""

import csv
import os
import sys
import re
import logging
import hashlib
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote

try:
    from PIL import Image, ImageOps
except ImportError:
    print("❌ مكتبة Pillow غير مثبتة. شغّل: pip install Pillow")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# استيراد engine الضغط من seo_helpers (مشترك مع شوبيفاي)
try:
    from seo_helpers import compress_image_seo
    COMPRESS_ENGINE_AVAILABLE = True
except ImportError:
    COMPRESS_ENGINE_AVAILABLE = False

try:
    from video_helpers import (
        check_ffmpeg, compress_video_seo, generate_video_thumbnail,
        generate_video_seo_filename, generate_video_thumbnail_filename,
        generate_video_alt_text, VIDEO_EXTENSIONS
    )
    VIDEO_AVAILABLE = check_ffmpeg()
except ImportError:
    VIDEO_AVAILABLE = False

# استيراد دوال SEO الخاصة بووردبريس
from wordpress_seo_helpers import (
    wp_build_slug, wp_extract_product_info,
    wp_generate_seo_filename, wp_generate_alt_text,
    WPSEOLogger, _is_arabic
)

# إصلاح ترميز الكونسول على ويندوز
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


# ─────────────────────────────────────────────
# ألوان الكونسول
# ─────────────────────────────────────────────
class Colors:
    """ANSI color codes for console output."""
    if sys.platform == "win32":
        os.system("")
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ─────────────────────────────────────────────
# 1. قراءة ملف CSV من WooCommerce
# ─────────────────────────────────────────────
class WooCommerceCSVParser:
    """
    يقرأ ملف CSV المُصدّر من WooCommerce ويجمع بيانات كل منتج.

    أعمدة WooCommerce المدعومة:
      ID, Type, SKU, Name, Published, Short description, Description,
      Categories, Tags, Images (مفصولة بـ |)
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.products = {}  # sku_or_id -> {name, sku, images[], ...}
        self.headers = []
        self.logger = logging.getLogger("WPCSVParser")

    def _detect_encoding(self) -> str:
        """محاولة اكتشاف ترميز الملف تلقائيًا."""
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1256', 'windows-1256']
        for enc in encodings:
            try:
                with open(self.csv_path, 'r', encoding=enc) as f:
                    f.read(2048)
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
        قراءة ملف WooCommerce CSV وتجميع بيانات كل منتج.

        WooCommerce CSV يختلف عن Shopify:
        - كل منتج في صف واحد (مش صفوف متعددة)
        - الصور في عمود واحد مفصولة بـ |
        - المعرّف: SKU أو ID (مش Handle)
        """
        if not os.path.exists(self.csv_path):
            print(f"{Colors.RED}❌ الملف غير موجود: {self.csv_path}{Colors.RESET}")
            return {}

        encoding = self._detect_encoding()
        self.logger.info(f"ترميز الملف: {encoding}")

        with open(self.csv_path, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f)
            self.headers = next(reader)
            headers = self.headers

            # ── الأعمدة الأساسية ──
            id_idx = self._find_column(headers, ['ID', 'id', 'Product ID', 'product_id'])
            name_idx = self._find_column(headers, ['Name', 'name', 'Title', 'title', 'Product Name', 'post_title'])
            sku_idx = self._find_column(headers, ['SKU', 'sku'])
            images_idx = self._find_column(headers, ['Images', 'images', 'Image', 'image', 'Image URL', 'image_url'])
            type_idx = self._find_column(headers, ['Type', 'type', 'Product Type'])
            categories_idx = self._find_column(headers, ['Categories', 'categories', 'Category', 'category'])
            tags_idx = self._find_column(headers, ['Tags', 'tags'])
            short_desc_idx = self._find_column(headers, [
                'Short description', 'short_description',
                'Short Description', 'Excerpt', 'excerpt',
                'post_excerpt'
            ])
            desc_idx = self._find_column(headers, [
                'Description', 'description', 'post_content',
                'Body', 'body'
            ])
            published_idx = self._find_column(headers, ['Published', 'published', 'Status', 'status'])

            # التحقق من الأعمدة الضرورية
            if name_idx == -1:
                print(f"{Colors.RED}❌ لم يتم العثور على عمود 'Name' في الملف{Colors.RESET}")
                print(f"   الأعمدة الموجودة: {headers}")
                return {}

            print(f"{Colors.GREEN}✅ تم اكتشاف أعمدة WooCommerce CSV بنجاح{Colors.RESET}")

            # عرض الأعمدة المكتشفة
            found_cols = ['Name']
            if id_idx != -1: found_cols.append('ID')
            if sku_idx != -1: found_cols.append('SKU')
            if images_idx != -1: found_cols.append('Images')
            if categories_idx != -1: found_cols.append('Categories')
            if tags_idx != -1: found_cols.append('Tags')
            if short_desc_idx != -1: found_cols.append('Short Description')
            print(f"   📋 أعمدة: {', '.join(found_cols)}")

            row_count = 0
            for row in reader:
                row_count += 1
                name = self._safe_get(row, name_idx)
                if not name:
                    continue

                # المعرّف الفريد: SKU أولاً، ثم ID، ثم اسم المنتج
                sku = self._safe_get(row, sku_idx)
                prod_id = self._safe_get(row, id_idx)
                key = sku or prod_id or name

                # تخطي المنتجات المكررة
                if key in self.products:
                    continue

                # تجميع الصور (مفصولة بـ | في WooCommerce)
                images = []
                raw_images = self._safe_get(row, images_idx)
                if raw_images:
                    for img_url in raw_images.split('|'):
                        img_url = img_url.strip()
                        if img_url:
                            images.append({
                                'url': img_url,
                                'position': len(images) + 1,
                            })

                self.products[key] = {
                    'name': name,
                    'sku': sku,
                    'id': prod_id,
                    'type': self._safe_get(row, type_idx),
                    'categories': self._safe_get(row, categories_idx),
                    'tags': self._safe_get(row, tags_idx),
                    'short_description': self._safe_get(row, short_desc_idx),
                    'description': self._safe_get(row, desc_idx),
                    'published': self._safe_get(row, published_idx),
                    'images': images,
                }

        # إحصائيات
        total_images = sum(len(p['images']) for p in self.products.values())
        print(f"\n{Colors.CYAN}📊 ملخص ملف WooCommerce:{Colors.RESET}")
        print(f"   📦 عدد المنتجات: {Colors.BOLD}{len(self.products)}{Colors.RESET}")
        print(f"   🖼️  عدد الصور: {Colors.BOLD}{total_images}{Colors.RESET}")
        print(f"   📄 عدد الصفوف: {Colors.BOLD}{row_count}{Colors.RESET}")

        return self.products


# ─────────────────────────────────────────────
# 2. ضغط وتحسين الصور — لووردبريس
# ─────────────────────────────────────────────
class WordPressImageCompressor:
    """
    ضغط الصور وتحويلها لـ WebP مع تحسين SEO لووردبريس.

    يستخدم:
    - compress_image_seo() من seo_helpers.py للضغط الفعلي
    - wordpress_seo_helpers.py للتسمية والـ Alt Text
    """

    TARGET_MAX_SIZE = 200 * 1024   # 200 KB (WordPress recommendation)
    MAX_DIMENSION = 2048           # أقصى بُعد 2048px

    def __init__(self, input_dir: str = "downloaded_images",
                 output_dir: str = "compressed_images", quality: int = 85):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.quality = quality
        self.logger = logging.getLogger("WPCompressor")
        self.stats = {
            'processed': 0, 'failed': 0,
            'original_size': 0, 'compressed_size': 0,
            'converted_webp': 0,
            'videos_processed': 0, 'videos_failed': 0,
            'videos_original_size': 0, 'videos_compressed_size': 0,
            'thumbnails_generated': 0,
        }
        # خريطة SEO: key → [{position, old_name, new_name, alt_text}]
        self.seo_map = {}

    def _sanitize_dirname(self, name: str) -> str:
        """تنظيف اسم المجلد."""
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = sanitized.strip('. ')
        return sanitized if sanitized else 'unknown_product'

    def _compress_single(self, src_path, dst_path):
        """ضغط صورة واحدة باستخدام engine الضغط المشترك."""
        if COMPRESS_ENGINE_AVAILABLE:
            return compress_image_seo(
                src_path, dst_path,
                target_min_kb=80, target_max_kb=200,
                max_dimension=self.MAX_DIMENSION
            )
        else:
            # Fallback بسيط لو seo_helpers مش موجود
            os.makedirs(os.path.dirname(dst_path) or '.', exist_ok=True)
            original_size = os.path.getsize(src_path)
            with Image.open(src_path) as img:
                # تصحيح اتجاه الصورة بناءً على EXIF Orientation tag
                img = ImageOps.exif_transpose(img)
                if img.mode == 'RGBA':
                    alpha = img.getchannel('A')
                    if alpha.getextrema() == (255, 255):
                        img = img.convert('RGB')
                elif img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                w, h = img.size
                if w > self.MAX_DIMENSION or h > self.MAX_DIMENSION:
                    ratio = min(self.MAX_DIMENSION / w, self.MAX_DIMENSION / h)
                    img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                dims_before = (w, h)
                dims_after = img.size
                img.save(dst_path, 'WEBP', quality=self.quality, method=4, optimize=True)
            compressed_size = os.path.getsize(dst_path)
            return {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'dimensions_before': dims_before,
                'dimensions_after': dims_after,
                'quality_used': self.quality,
            }

    def compress_all_seo(self, products: dict, seo_logger=None,
                         progress_callback=None) -> dict:
        """
        ضغط جميع الصور مع تحسين SEO لووردبريس.

        Args:
            products: dict من WooCommerceCSVParser.parse() أو من بناء يدوي
            seo_logger: WPSEOLogger instance
            progress_callback: callable(done, total) → True/False

        Returns:
            dict: إحصائيات الضغط
        """
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}🗜️  ضغط + تحسين SEO للصور (WordPress)...{Colors.RESET}")
        print(f"   حجم مستهدف: 80-200 KB | أقصى بُعد: 2048px | صيغة: WebP")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        if not os.path.exists(self.input_dir):
            print(f"{Colors.RED}❌ مجلد الصور غير موجود: {self.input_dir}{Colors.RESET}")
            return self.stats

        # بناء قائمة المهام
        tasks = []
        for key, product in products.items():
            handle_dir = self._sanitize_dirname(key)
            src_dir = os.path.join(self.input_dir, handle_dir)

            if not os.path.exists(src_dir):
                continue

            existing_files = sorted([
                f for f in os.listdir(src_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'))
            ])

            # جمع الفيديوهات
            existing_videos = []
            if VIDEO_AVAILABLE:
                existing_videos = sorted([
                    f for f in os.listdir(src_dir)
                    if f.lower().endswith(VIDEO_EXTENSIONS)
                ])

            if not existing_files and not existing_videos:
                continue

            # بيانات SEO
            name = product.get('name', '') or key
            sku = product.get('sku', '') or ''
            categories = product.get('categories', '') or ''
            short_desc = product.get('short_description', '') or ''
            tags = product.get('tags', '') or ''

            slug = wp_build_slug(name, sku, categories)
            info = wp_extract_product_info(name, categories, short_desc)
            total_imgs = len(existing_files)

            metadata = {
                'description_snippet': info['description_snippet'],
                'tags': tags,
                'sku': sku,
            }

            for idx, filename in enumerate(existing_files):
                position = idx + 1
                src_path = os.path.join(src_dir, filename)

                seo_filename = wp_generate_seo_filename(slug, position, total_imgs)
                dst_dir = os.path.join(self.output_dir, handle_dir)
                dst_path = os.path.join(dst_dir, seo_filename)

                alt_text = wp_generate_alt_text(
                    info['product_name'], info['main_category'],
                    position, total_imgs, metadata
                )

                tasks.append({
                    'key': key, 'name': name, 'sku': sku,
                    'position': position, 'src_path': src_path,
                    'dst_path': dst_path, 'old_name': filename,
                    'new_name': seo_filename, 'alt_text': alt_text,
                    'type': 'image',
                })

            # ── مهام الفيديو ──
            for vidx, vfilename in enumerate(existing_videos):
                vid_position = vidx + 1
                vid_src_path = os.path.join(src_dir, vfilename)
                vid_seo_filename = generate_video_seo_filename(slug, vid_position, len(existing_videos))
                vid_dst_dir = os.path.join(self.output_dir, handle_dir)
                vid_dst_path = os.path.join(vid_dst_dir, vid_seo_filename)
                vid_alt_text = generate_video_alt_text(
                    info['product_name'], info['main_category'],
                    vid_position, len(existing_videos), metadata
                )
                thumb_filename = generate_video_thumbnail_filename(slug, vid_position)
                thumb_path = os.path.join(vid_dst_dir, thumb_filename)

                tasks.append({
                    'key': key, 'name': name, 'sku': sku,
                    'position': vid_position, 'src_path': vid_src_path,
                    'dst_path': vid_dst_path, 'old_name': vfilename,
                    'new_name': vid_seo_filename, 'alt_text': vid_alt_text,
                    'type': 'video',
                    'thumb_path': thumb_path, 'thumb_filename': thumb_filename,
                })

        if not tasks:
            print(f"{Colors.YELLOW}⚠️ لا توجد صور أو فيديوهات للضغط{Colors.RESET}")
            return self.stats

        # تنفيذ الضغط
        iterator = tasks
        if tqdm:
            iterator = tqdm(tasks, desc="🗜️  WP SEO ضغط", unit="ملف",
                            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

        for task in iterator:
            try:
                if task.get('type') == 'video':
                    # ── ضغط فيديو ──
                    vid_stats = compress_video_seo(
                        task['src_path'], task['dst_path'],
                        max_dimension=1080, target_quality='balanced'
                    )
                    self.stats['videos_original_size'] += vid_stats['original_size']
                    self.stats['videos_compressed_size'] += vid_stats['compressed_size']
                    self.stats['videos_processed'] += 1

                    # توليد Thumbnail
                    try:
                        generate_video_thumbnail(task['src_path'], task['thumb_path'])
                        self.stats['thumbnails_generated'] += 1
                    except Exception:
                        pass

                    k = task['key']
                    if k not in self.seo_map:
                        self.seo_map[k] = []
                    self.seo_map[k].append({
                        'position': task['position'],
                        'old_name': task['old_name'],
                        'new_name': task['new_name'],
                        'alt_text': task['alt_text'],
                        'type': 'video',
                        'thumbnail': task.get('thumb_filename', ''),
                    })

                else:
                    # ── ضغط صورة (كالعادة) ──
                    comp_stats = self._compress_single(
                        task['src_path'], task['dst_path']
                    )

                    self.stats['original_size'] += comp_stats['original_size']
                    self.stats['compressed_size'] += comp_stats['compressed_size']
                    self.stats['processed'] += 1
                    self.stats['converted_webp'] += 1

                    k = task['key']
                    if k not in self.seo_map:
                        self.seo_map[k] = []
                    self.seo_map[k].append({
                        'position': task['position'],
                        'old_name': task['old_name'],
                        'new_name': task['new_name'],
                        'alt_text': task['alt_text'],
                    })

                    if seo_logger:
                        seo_logger.add_entry(
                            product_name=task['name'],
                            sku=task['sku'],
                            position=task['position'],
                            old_filename=task['old_name'],
                            new_filename=task['new_name'],
                            alt_text=task['alt_text'],
                            compress_stats=comp_stats,
                        )

            except Exception as e:
                if task.get('type') == 'video':
                    self.stats['videos_failed'] += 1
                else:
                    self.stats['failed'] += 1
                self.logger.error(f"فشل ضغط {task['src_path']}: {e}")

            if progress_callback:
                if progress_callback(self.stats['processed'], len(tasks)) is False:
                    break

        self._print_summary()
        return self.stats

    def compress_direct_images(self, seo_logger=None,
                               progress_callback=None) -> dict:
        """
        ضغط صور مباشرة بدون CSV (من مجلدات على الجهاز).
        يبني products dict من هيكل المجلدات تلقائياً.
        """
        products = {}
        if not os.path.exists(self.input_dir):
            return self.stats

        for root, dirs, files in os.walk(self.input_dir):
            rel_dir = os.path.relpath(root, self.input_dir)
            if rel_dir == '.':
                continue

            imgs = [f for f in files
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'))]
            if not imgs:
                continue

            parts = rel_dir.replace('\\', '/').split('/')
            handle = parts[0]

            if handle not in products:
                products[handle] = {
                    'name': handle.replace('-', ' ').replace('_', ' ').title(),
                    'sku': '',
                    'categories': '',
                    'tags': '',
                    'short_description': '',
                    'images': [],
                }

        return self.compress_all_seo(products, seo_logger, progress_callback)

    def _print_summary(self):
        """طباعة ملخص الضغط."""
        if self.stats['original_size'] > 0:
            savings = self.stats['original_size'] - self.stats['compressed_size']
            savings_pct = (savings / self.stats['original_size']) * 100

            print(f"\n{Colors.GREEN}✅ اكتمل الضغط (WordPress):{Colors.RESET}")
            print(f"   ✓ تم ضغط: {Colors.GREEN}{self.stats['processed']}{Colors.RESET} صورة")
            print(f"   ✓ تم تحويل لـ WebP: {Colors.CYAN}{self.stats['converted_webp']}{Colors.RESET}")
            if self.stats['failed'] > 0:
                print(f"   ✗ فشل: {Colors.RED}{self.stats['failed']}{Colors.RESET}")
            print(f"   📦 الحجم الأصلي:  {self._format_size(self.stats['original_size'])}")
            print(f"   📦 بعد الضغط:     {self._format_size(self.stats['compressed_size'])}")
            print(f"   💰 التوفير:       {Colors.GREEN}{Colors.BOLD}"
                  f"{self._format_size(savings)} ({savings_pct:.1f}%){Colors.RESET}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """تحويل الحجم من بايت إلى صيغة مقروءة."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# ─────────────────────────────────────────────
# 3. تصدير CSV محسّن لـ WooCommerce
# ─────────────────────────────────────────────
class WooCommerceCSVExporter:
    """
    تصدير CSV محسّن لـ WooCommerce مع أسماء ملفات SEO.

    يقرأ الملف الأصلي ويحدّث عمود Images بأسماء الملفات الجديدة.
    """

    def __init__(self, original_csv: str, seo_map: dict, output_path: str = None):
        self.original_csv = original_csv
        self.seo_map = seo_map
        if output_path:
            self.output_path = output_path
        else:
            base = os.path.splitext(original_csv)[0]
            self.output_path = f"{base}_wp_optimized.csv"

    def export(self) -> str:
        """تصدير الملف المحسّن."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}📄 تصدير CSV محسّن لـ WooCommerce...{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

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

        rows_modified = 0
        with open(self.original_csv, 'r', encoding=encoding, newline='') as fin:
            reader = csv.reader(fin)
            headers = next(reader)
            headers_lower = [h.strip().lower() for h in headers]

            # البحث عن الأعمدة
            name_idx = -1
            for possible in ['name', 'title', 'product name', 'post_title']:
                if possible in headers_lower:
                    name_idx = headers_lower.index(possible)
                    break

            sku_idx = -1
            if 'sku' in headers_lower:
                sku_idx = headers_lower.index('sku')

            id_idx = -1
            if 'id' in headers_lower:
                id_idx = headers_lower.index('id')

            images_idx = -1
            for possible in ['images', 'image', 'image url', 'image_url']:
                if possible in headers_lower:
                    images_idx = headers_lower.index(possible)
                    break

            if images_idx == -1 or name_idx == -1:
                print(f"{Colors.RED}❌ لم يتم العثور على أعمدة Name/Images{Colors.RESET}")
                return ''

            all_rows = [headers]
            for row in reader:
                while len(row) < len(headers):
                    row.append('')

                name = row[name_idx].strip() if name_idx < len(row) else ''
                sku = row[sku_idx].strip() if sku_idx != -1 and sku_idx < len(row) else ''
                prod_id = row[id_idx].strip() if id_idx != -1 and id_idx < len(row) else ''
                key = sku or prod_id or name

                if key and key in self.seo_map:
                    entries = self.seo_map[key]
                    # بناء قائمة الصور الجديدة مفصولة بـ |
                    new_images = '|'.join(
                        e['new_name'] for e in sorted(entries, key=lambda x: x['position'])
                    )
                    row[images_idx] = new_images
                    rows_modified += 1

                all_rows.append(row)

        # كتابة الملف
        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as fout:
            writer = csv.writer(fout)
            writer.writerows(all_rows)

        print(f"{Colors.GREEN}✅ تم تصدير CSV محسّن لـ WooCommerce:{Colors.RESET}")
        print(f"   📄 الملف: {Colors.BOLD}{self.output_path}{Colors.RESET}")
        print(f"   ✏️  منتجات معدّلة: {Colors.CYAN}{rows_modified}{Colors.RESET}")
        print(f"   📊 عمود محدّث: Images (أسماء ملفات SEO)")

        return self.output_path


# ─────────────────────────────────────────────
# 4. تصدير مرجع Alt Text
# ─────────────────────────────────────────────
class WordPressAltTextExporter:
    """
    تصدير ملف مرجعي للـ Alt Text — للنسخ اليدوي في مكتبة الميديا.

    يُنتج:
    1. CSV سهل القراءة
    2. HTML جميل بجدول مرتب
    """

    def __init__(self, seo_map: dict, products: dict, output_dir: str):
        self.seo_map = seo_map
        self.products = products
        self.output_dir = output_dir

    def export_csv(self) -> str:
        """تصدير مرجع Alt Text كـ CSV."""
        csv_path = os.path.join(self.output_dir, 'wp_alt_text_reference.csv')

        headers = ['Product Name', 'SKU', 'Image Filename', 'Alt Text', 'Position']
        rows = []

        for key, entries in self.seo_map.items():
            product = self.products.get(key, {})
            name = product.get('name', key)
            sku = product.get('sku', '')

            for entry in sorted(entries, key=lambda x: x['position']):
                rows.append({
                    'Product Name': name,
                    'SKU': sku,
                    'Image Filename': entry['new_name'],
                    'Alt Text': entry['alt_text'],
                    'Position': entry['position'],
                })

        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        print(f"   📋 Alt Text CSV: {Colors.BOLD}{csv_path}{Colors.RESET}")
        return csv_path

    def export_html(self) -> str:
        """تصدير مرجع Alt Text كـ HTML جميل — سهل النسخ."""
        html_path = os.path.join(self.output_dir, 'wp_alt_text_reference.html')

        html_content = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Alt Text Reference</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f172a; color: #e2e8f0;
            padding: 20px; line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            text-align: center; margin-bottom: 8px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 28px;
        }
        .subtitle {
            text-align: center; color: #94a3b8; margin-bottom: 30px;
            font-size: 14px;
        }
        .product-card {
            background: #1e293b; border-radius: 12px;
            margin-bottom: 20px; overflow: hidden;
            border: 1px solid #334155;
        }
        .product-header {
            background: linear-gradient(135deg, #1e3a5f, #1e293b);
            padding: 15px 20px; border-bottom: 1px solid #334155;
        }
        .product-header h2 { font-size: 18px; color: #60a5fa; }
        .product-header .sku { color: #94a3b8; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #0f172a; padding: 10px 15px;
            text-align: left; font-size: 12px;
            color: #94a3b8; text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        td { padding: 12px 15px; border-bottom: 1px solid #1e293b; }
        tr:hover td { background: #1a2744; }
        .filename { color: #34d399; font-family: 'Consolas', monospace; font-size: 13px; }
        .alt-text {
            color: #fbbf24; cursor: pointer; position: relative;
            font-size: 13px;
        }
        .alt-text:hover { text-decoration: underline; }
        .alt-text::after {
            content: '📋 Click to copy';
            position: absolute; bottom: 100%; left: 0;
            background: #334155; color: #e2e8f0;
            padding: 4px 8px; border-radius: 4px;
            font-size: 11px; white-space: nowrap;
            opacity: 0; transition: opacity 0.2s;
            pointer-events: none;
        }
        .alt-text:hover::after { opacity: 1; }
        .pos { color: #94a3b8; text-align: center; font-weight: bold; }
        .copied {
            position: fixed; top: 20px; right: 20px;
            background: #22c55e; color: white;
            padding: 10px 20px; border-radius: 8px;
            font-weight: bold; display: none; z-index: 1000;
        }
        .stats {
            display: flex; justify-content: center; gap: 30px;
            margin-bottom: 25px;
        }
        .stat-item {
            background: #1e293b; padding: 12px 24px;
            border-radius: 8px; text-align: center;
            border: 1px solid #334155;
        }
        .stat-value { font-size: 24px; font-weight: bold; color: #60a5fa; }
        .stat-label { font-size: 12px; color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖼️ WordPress Alt Text Reference</h1>
        <p class="subtitle">Click any alt text to copy it to clipboard — then paste in WordPress Media Library</p>
        <div class="copied" id="copiedMsg">✅ Copied to clipboard!</div>
"""
        # إحصائيات
        total_products = len(self.seo_map)
        total_images = sum(len(entries) for entries in self.seo_map.values())
        html_content += f"""
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{total_products}</div>
                <div class="stat-label">Products</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{total_images}</div>
                <div class="stat-label">Images</div>
            </div>
        </div>
"""

        # جداول المنتجات
        for key, entries in self.seo_map.items():
            product = self.products.get(key, {})
            name = product.get('name', key)
            sku = product.get('sku', '')

            html_content += f"""
        <div class="product-card">
            <div class="product-header">
                <h2>{self._html_escape(name)}</h2>
                <span class="sku">{'SKU: ' + self._html_escape(sku) if sku else ''}</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width:5%">#</th>
                        <th style="width:35%">Image Filename</th>
                        <th style="width:60%">Alt Text (click to copy)</th>
                    </tr>
                </thead>
                <tbody>
"""
            for entry in sorted(entries, key=lambda x: x['position']):
                alt_escaped = self._html_escape(entry['alt_text'])
                html_content += f"""                    <tr>
                        <td class="pos">{entry['position']}</td>
                        <td class="filename">{self._html_escape(entry['new_name'])}</td>
                        <td class="alt-text" onclick="copyAlt(this)">{alt_escaped}</td>
                    </tr>
"""
            html_content += """                </tbody>
            </table>
        </div>
"""

        # JavaScript للنسخ
        html_content += """
    </div>
    <script>
        function copyAlt(el) {
            const text = el.textContent;
            navigator.clipboard.writeText(text).then(() => {
                const msg = document.getElementById('copiedMsg');
                msg.style.display = 'block';
                msg.textContent = '✅ Copied: ' + text.substring(0, 40) + '...';
                setTimeout(() => { msg.style.display = 'none'; }, 2000);
            });
        }
    </script>
</body>
</html>
"""
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"   🌐 Alt Text HTML: {Colors.BOLD}{html_path}{Colors.RESET}")
        return html_path

    @staticmethod
    def _html_escape(text):
        """تحويل الأحرف الخاصة لـ HTML entities."""
        return (text.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))

    def export_all(self):
        """تصدير CSV + HTML."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}📋 تصدير مرجع Alt Text لووردبريس...{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")

        csv_path = self.export_csv()
        html_path = self.export_html()

        return csv_path, html_path


# ─────────────────────────────────────────────
# 5. تقرير WordPress
# ─────────────────────────────────────────────
class WordPressReportGenerator:
    """إنشاء تقرير شامل بنتائج العملية لووردبريس."""

    def __init__(self, output_path: str = "wp_report.txt"):
        self.output_path = output_path

    def generate(self, products: dict, compress_stats: dict):
        """إنشاء التقرير النهائي."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_images = sum(len(p.get('images', [])) for p in products.values())

        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║       تقرير أداة صور ووردبريس بالجملة                  ║",
            "║       WordPress Bulk Image Tool Report                  ║",
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
                f"  📦 الحجم الأصلي: {WordPressImageCompressor._format_size(original)}",
                f"  📦 بعد الضغط: {WordPressImageCompressor._format_size(compressed)}",
                f"  💰 التوفير: {WordPressImageCompressor._format_size(savings)} ({savings_pct:.1f}%)",
                "",
            ])

        # تفاصيل المنتجات
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 تفاصيل المنتجات",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ])

        for key, product in products.items():
            name = product.get('name', key)
            sku = product.get('sku', '')
            img_count = len(product.get('images', []))
            sku_label = f" [SKU: {sku}]" if sku else ""
            lines.append(f"  📦 {name}{sku_label} - {img_count} صور")

        lines.extend(["", "═══════════════════════════════════════════", ""])

        report_content = "\n".join(lines)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"\n{Colors.GREEN}📊 تم حفظ التقرير: {Colors.BOLD}{self.output_path}{Colors.RESET}")
        return report_content
