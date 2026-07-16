#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress SEO Helper Functions — General Purpose
متوافق مع معايير WordPress SEO 2026 — لكل أنواع المنتجات

هذا الملف مستقل تماماً عن seo_helpers.py (شوبيفاي).

القواعد المُطبَّقة:
  • اسم الملف: lowercase، hyphens فقط، وصف المنتج
  • Alt text: 60-90 حرف، جملة طبيعية، بدون "image of"
  • حجم الصورة: < 200 KB
  • الأبعاد: <= 2048px
  • الصيغة: WebP
"""

import os
import re
import csv
import hashlib
import html as html_module


# ═══════════════════════════════════════════════════════════════
# 1. ثوابت
# ═══════════════════════════════════════════════════════════════

# كلمات ضوضاء عامة تُحذف من اسم الملف (لأي مجال)
FILENAME_NOISE = {
    'product', 'item', 'new', 'sale', 'best', 'hot', 'top',
    'buy', 'shop', 'store', 'online', 'free', 'shipping',
    'the', 'a', 'an', 'and', 'or', 'of', 'in', 'for', 'to',
    'with', 'by', 'from', 'at', 'on', 'is', 'it', 'as',
    'copy', 'img', 'image', 'photo', 'pic', 'picture',
    'default', 'untitled', 'unnamed', 'placeholder',
}

# أوصاف عامة حسب ترتيب الصورة — تناسب أي منتج
POSITION_DESCRIPTORS = {
    1: 'main-product-image',
    2: 'detail-view',
    3: 'gallery-view',
    4: 'additional-angle',
    5: 'product-showcase',
}


# ═══════════════════════════════════════════════════════════════
# 2. دوال مساعدة داخلية
# ═══════════════════════════════════════════════════════════════

def _is_arabic(text):
    """هل النص يحتوي حروف عربية؟"""
    return bool(re.search(
        r'[\u0600-\u06FF\u0660-\u0669\u06F0-\u06F9]',
        str(text)
    ))


def _strip_html(html_text):
    """إزالة وسوم HTML وتنظيف المسافات."""
    if not html_text:
        return ''
    text = html_module.unescape(str(html_text))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _to_slug(text):
    """تحويل نص لـ URL slug نظيف (lowercase + hyphens فقط)."""
    text = text.lower().strip()
    text = re.sub(r"[''`]", '', text)
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-{2,}', '-', text)
    return text.strip('-')


def _truncate_alt(text, max_chars=90):
    """
    اقتصاص Alt Text لـ <= 90 حرف (WordPress 2026: 60-90 حرف).
    يقطع عند آخر كلمة كاملة قبل الحد.
    """
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > 20:
        return truncated[:last_space].rstrip(' ,-')
    return truncated.rstrip(' ,-')


def _extract_keywords_from_description(description, max_words=6):
    """
    استخراج كلمات مفتاحية من وصف المنتج (إنجليزي فقط).
    يرجع أول كلمات مفيدة بدون ضوضاء.
    """
    text = _strip_html(description)
    if not text:
        return ''

    words = []
    for w in text.split():
        if _is_arabic(w):
            continue
        clean = re.sub(r'[^a-zA-Z0-9]', '', w)
        if clean and clean.lower() not in FILENAME_NOISE and len(clean) > 1:
            words.append(clean)
        if len(words) >= max_words:
            break

    return ' '.join(words)


# ═══════════════════════════════════════════════════════════════
# 3. بناء Slug فريد للمنتج
# ═══════════════════════════════════════════════════════════════

def wp_build_slug(name, sku='', categories=''):
    """
    بناء slug فريد من اسم المنتج + SKU.

    يعمل مع أي نوع منتج (عطور، إلكترونيات، ملابس، أكل، إلخ).

    Args:
        name: اسم المنتج (مثل: "Samsung Galaxy S24 Ultra 256GB")
        sku: رمز المنتج (مثل: "SAM-S24U-256")
        categories: تصنيفات المنتج (مثل: "Electronics > Phones")

    Returns:
        str: slug نظيف فريد (مثل: "samsung-galaxy-s24-ultra-256gb-a1b2")
    """
    # استخراج الكلمات الإنجليزية من الاسم
    clean_words = []
    if name:
        for w in name.split():
            if _is_arabic(w):
                continue
            w_clean = re.sub(r'[^a-z0-9]', '', w.lower())
            if w_clean and w_clean not in FILENAME_NOISE and len(w_clean) > 0:
                clean_words.append(w_clean)

    slug = '-'.join(clean_words[:8])  # أقصى 8 كلمات

    # لو الاسم فاضي (عربي بالكامل) — استخدم التصنيف
    if not slug and categories:
        cat_parts = categories.replace('>', ',').split(',')
        for part in cat_parts:
            part = part.strip()
            if part and not _is_arabic(part):
                slug = _to_slug(part)
                break

    # لو لسه فاضي — استخدم SKU
    if not slug and sku:
        slug = _to_slug(sku)

    if not slug:
        slug = 'product'

    # تنظيف نهائي
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')

    # إضافة hash قصير للتفريد (4 أحرف من MD5)
    source = f"{name or ''}-{sku or ''}"
    h4 = hashlib.md5(source.encode('utf-8', errors='replace')).hexdigest()[:4]
    return f"{slug}-{h4}"


# ═══════════════════════════════════════════════════════════════
# 4. استخراج معلومات المنتج
# ═══════════════════════════════════════════════════════════════

def wp_extract_product_info(name, categories='', short_description=''):
    """
    استخراج معلومات المنتج من بيانات WooCommerce.

    يعمل مع أي مجال — يستخرج:
    - اسم المنتج (إنجليزي)
    - التصنيف الرئيسي
    - ملخص الوصف

    Args:
        name: اسم المنتج
        categories: التصنيفات (مفصولة بـ > أو ,)
        short_description: الوصف المختصر

    Returns:
        dict: {product_name, main_category, description_snippet}
    """
    # استخراج اسم المنتج (إنجليزي فقط)
    product_name = ''
    if name:
        eng_parts = []
        for w in name.split():
            if _is_arabic(w):
                continue
            clean = re.sub(r'[^\w\'-]', '', w).strip("'-")
            if clean:
                eng_parts.append(clean)
        product_name = ' '.join(eng_parts)

    if not product_name:
        product_name = name or 'Product'

    # التصنيف الرئيسي
    main_category = ''
    if categories:
        # WooCommerce يستخدم > للتصنيفات الفرعية و , للتصنيفات المتعددة
        parts = categories.replace('>', ',').split(',')
        for part in parts:
            part = part.strip()
            if part and not _is_arabic(part):
                main_category = part
                break

    # ملخص الوصف
    description_snippet = ''
    if short_description:
        description_snippet = _extract_keywords_from_description(
            short_description, max_words=6
        )

    return {
        'product_name': product_name.strip(),
        'main_category': main_category.strip(),
        'description_snippet': description_snippet.strip(),
    }


# ═══════════════════════════════════════════════════════════════
# 5. توليد اسم الملف SEO
# ═══════════════════════════════════════════════════════════════

def wp_generate_seo_filename(clean_slug, position, total_images):
    """
    توليد اسم ملف WordPress SEO-friendly.

    المعايير (WordPress 2026):
    - lowercase فقط
    - hyphens بين الكلمات
    - وصفي (مش أرقام عشوائية)
    - بدون مسافات أو رموز خاصة
    - صيغة WebP

    Args:
        clean_slug: الـ slug النظيف من wp_build_slug()
        position: ترتيب الصورة (1-based)
        total_images: إجمالي صور المنتج

    Returns:
        str: اسم الملف (مثل: "samsung-galaxy-s24-a1b2-main-product-image.webp")
    """
    if total_images == 1:
        desc = 'product-image'
    elif position in POSITION_DESCRIPTORS:
        desc = POSITION_DESCRIPTORS[position]
    else:
        desc = f'image-{position}'

    filename = f'{clean_slug}-{desc}.webp'
    filename = re.sub(r'-{2,}', '-', filename)
    return filename.lower()


# ═══════════════════════════════════════════════════════════════
# 6. توليد Alt Text
# ═══════════════════════════════════════════════════════════════

def wp_generate_alt_text(product_name, main_category='', position=1,
                         total_images=1, metadata=None):
    """
    توليد Alt Text متوافق مع WordPress SEO 2026.

    القواعد:
      • 60-90 حرف (الأمثل لـ WordPress + Yoast/RankMath)
      • يبدأ باسم المنتج
      • جملة طبيعية وصفية
      • لا يبدأ بـ "image of" أو "picture of"
      • جملة مختلفة لكل صورة
      • لا keyword stuffing
      • يعمل مع أي مجال (عطور، إلكترونيات، ملابس، أكل، إلخ)

    Args:
        product_name: اسم المنتج
        main_category: التصنيف الرئيسي
        position: ترتيب الصورة
        total_images: إجمالي الصور
        metadata: dict اختياري: {description_snippet, tags, sku}
    """
    metadata = metadata or {}
    product = (product_name or 'Product').strip()
    category = (main_category or '').strip()
    snippet = (metadata.get('description_snippet', '') or '').strip()
    tags = (metadata.get('tags', '') or '').strip()

    # استخراج أول tag مفيد (إنجليزي)
    first_tag = ''
    if tags:
        for t in tags.replace(';', ',').split(','):
            t = t.strip()
            if t and not _is_arabic(t):
                first_tag = t
                break

    # ── بناء Alt Text حسب الـ position ──

    if total_images == 1:
        # صورة وحيدة — أقصى معلومات
        if category and snippet:
            alt = f'{product} - {category} - {snippet}'
        elif category:
            alt = f'{product} - {category} - high quality product'
        elif snippet:
            alt = f'{product} - {snippet}'
        else:
            alt = f'{product} - premium quality product'

    elif position == 1:
        # الصورة الرئيسية
        if category:
            alt = f'{product} - {category}'
        else:
            alt = f'{product} - featured product view'

    elif position == 2:
        # تفاصيل المنتج
        if snippet:
            alt = f'{product} detailed view - {snippet}'
        elif first_tag:
            alt = f'{product} - {first_tag} collection'
        else:
            alt = f'{product} - close-up detail view'

    elif position == 3:
        # معرض
        if first_tag:
            alt = f'{product} - {first_tag} product gallery'
        elif category:
            alt = f'{product} - {category} gallery view'
        else:
            alt = f'{product} - product gallery showcase'

    elif position == 4:
        # زاوية إضافية
        if snippet:
            alt = f'{product} additional angle - {snippet}'
        else:
            alt = f'{product} - additional product angle'

    else:
        # صور إضافية (5+)
        alt = f'{product} - product view {position}'

    # ── ضمان 60-90 حرف ──
    return _truncate_alt(alt, max_chars=90)


# ═══════════════════════════════════════════════════════════════
# 7. WordPress SEO Logger
# ═══════════════════════════════════════════════════════════════

class WPSEOLogger:
    """
    تسجيل تفاصيل تحسين SEO لكل صورة في ملف CSV للمراجعة.

    الأعمدة:
      Product Name | SKU | Position | Old Filename | New Filename
      Alt Text | Alt Length | Size Before (KB) | Size After (KB)
      Dimensions Before | Dimensions After | Quality Used
    """

    HEADERS = [
        'Product Name', 'SKU', 'Position',
        'Old Filename', 'New Filename',
        'Alt Text', 'Alt Length',
        'Size Before (KB)', 'Size After (KB)',
        'Dimensions Before', 'Dimensions After', 'Quality Used',
    ]

    def __init__(self, log_path='wp_seo_optimization_log.csv'):
        self.log_path = log_path
        self.entries = []

    def add_entry(self, product_name, sku, position,
                  old_filename, new_filename, alt_text,
                  compress_stats=None):
        """إضافة سجل صورة واحدة."""
        entry = {
            'Product Name': product_name,
            'SKU': sku,
            'Position': position,
            'Old Filename': old_filename,
            'New Filename': new_filename,
            'Alt Text': alt_text,
            'Alt Length': len(alt_text),
            'Size Before (KB)': '',
            'Size After (KB)': '',
            'Dimensions Before': '',
            'Dimensions After': '',
            'Quality Used': '',
        }
        if compress_stats:
            entry['Size Before (KB)'] = \
                f"{compress_stats['original_size'] / 1024:.1f}"
            entry['Size After (KB)'] = \
                f"{compress_stats['compressed_size'] / 1024:.1f}"
            db = compress_stats['dimensions_before']
            da = compress_stats['dimensions_after']
            entry['Dimensions Before'] = f"{db[0]}x{db[1]}"
            entry['Dimensions After'] = f"{da[0]}x{da[1]}"
            entry['Quality Used'] = compress_stats['quality_used']
        self.entries.append(entry)

    def save(self):
        """حفظ السجل في CSV بترميز UTF-8 BOM."""
        with open(self.log_path, 'w', newline='',
                  encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            writer.writerows(self.entries)

    def get_summary(self):
        """ملخص مختصر."""
        total = len(self.entries)
        with_comp = [e for e in self.entries if e['Size After (KB)']]
        over_limit = [
            e for e in self.entries
            if e['Alt Length'] and int(e['Alt Length']) > 90
        ]
        msg = f"{total} images processed, {len(with_comp)} compressed"
        if over_limit:
            msg += f" ⚠️ {len(over_limit)} alt texts > 90 chars"
        return msg
