#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO Helper Functions — Shopify Image Tool
متوافق مع معايير Shopify SEO 2026

القواعد المُطبَّقة:
  • اسم الملف: lowercase، hyphens فقط، وصف حقيقي للمنتج
  • Alt text: < 125 حرف، جملة طبيعية، تتضمن البراند + اسم العطر
  • حجم الصورة: < 200 KB (Shopify يوصي < 250 KB لـ LCP)
  • الأبعاد: يُحافظ على الأصلية ما دامت <= 2048px
  • الصيغة: WebP دائماً
"""

import os
import re
import csv
import html as html_module
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════
# 1. ثوابت وكلمات الضوضاء
# ═══════════════════════════════════════════════════════════════

# كلمات تُحذف من URL/filename slug فقط (واسعة النطاق)
FILENAME_NOISE = {
    'decant', 'decants', 'original', 'perfume', 'parfum', 'extrait',
    'de', 'eau', 'edp', 'edt', 'collectors', 'edition', 'collector',
    'ml', 'by', 'for', 'men', 'women', 'and', 'the', 'in', 'of', 'a',
    'new', 'release',
    '5ml', '10ml', '15ml', '30ml', '50ml', '100ml',
    '2023', '2024', '2025', '2026', '2027',
}

# كلمات تُحذف عند استخراج اسم البراند/العطر من العنوان (ضيقة النطاق)
# ⚠️ مش بنشيل حروف الجر ('of','the','and') عشان أسماء زي "God of Fire"
TITLE_NOISE = {
    'decant', 'decants', 'perfume', 'parfum', 'extrait',
    'eau', 'edp', 'edt', 'ml', 'original',
    '5ml', '10ml', '15ml', '30ml', '50ml', '100ml',
    '2023', '2024', '2025', '2026', '2027',
}

# أوصاف تصف المنتج — مش محتوى الصورة — فمستحيل يكون فيه تخريف
# لأن المنتج فعلاً perfume decant بغض النظر عن الصورة هي إيه
POSITION_DESCRIPTORS = {
    1: 'perfume-decant',
    2: 'fragrance-detail',
    3: 'scent-collection',
    4: 'perfume-product',
}

# براندات عطور متعددة الكلمات — عشان يتعرف عليها كبراند واحد
# الـ key: lowercase بدون مسافات، الـ value: الاسم الصح
KNOWN_BRANDS = {
    'matierepremiere': 'Matiere Premiere',
    'bykilian': 'By Kilian',
    'jomalone': 'Jo Malone',
    'jomaloneلندن': 'Jo Malone',
    'lelabo': 'Le Labo',
    'losangeleslime': 'Los Angeles Lime',
    'victoriabecham': 'Victoria Beckham',
    'annickgoutal': 'Annick Goutal',
    'fredericmalle': 'Frederic Malle',
    'serge lutens': 'Serge Lutens',
    'sergelutens': 'Serge Lutens',
    'tomford': 'Tom Ford',
    'yslsaintlaurent': 'YSL',
    'giorgioarmani': 'Giorgio Armani',
    'carolinaherrera': 'Carolina Herrera',
    'ralphlauren': 'Ralph Lauren',
    'bvlgari': 'Bvlgari',
    'stephamblucas': 'SHL',
    'shl': 'SHL',
    'parfonvmvni': 'Parfums de Marly',
    'parfumsdemarly': 'Parfums de Marly',
    'maison': 'Maison Margiela',
    'maisonmargiela': 'Maison Margiela',
    'xerjoff': 'Xerjoff',
    'orientica': 'Orientica',
    'nishane': 'Nishane',
    'kilian': 'Kilian',
    'kiton': 'Kiton',
    'puredistance': 'Pure Distance',
    'ojardin': "O'Jardin",
    'francescabianchi': 'Francesca Bianchi',
    'initio': 'Initio',
    'erozenz': 'Erozenz',
    'goldfield': 'Goldfield & Banks',
}


# ═══════════════════════════════════════════════════════════════
# 2. دوال مساعدة داخلية
# ═══════════════════════════════════════════════════════════════

def _is_arabic(text):
    """هل الكلمة تحتوي حروف عربية؟"""
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


def _extract_notes_snippet(body_html, max_words=8):
    """
    استخراج ملخص نوتات العطر من Body HTML.
    يرجع أول 8 كلمات من نوتات العطر — إنجليزي فقط، بدون ضوضاء.
    """
    text = _strip_html(body_html)
    if not text:
        return ''

    patterns = [
        r'top\s+notes?[:\s]+([^.;<\n]+)',
        r'head\s+notes?[:\s]+([^.;<\n]+)',
        r'notes?\s+(?:of|include|are|:)\s*([^.;<\n]+)',
        r'(?:combines?|features?|opens?\s+with)[:\s]+([^.;<\n]+)',
        r'opening[:\s]+([^.;<\n]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            snippet = match.group(1).strip()
            # إزالة كلمات البداية الزائدة
            snippet = re.sub(
                r'^(?:are|is|of|include|includes|:)\s+',
                '', snippet, flags=re.IGNORECASE
            )
            # فلترة الكلمات العربية والرموز
            words = [
                w.strip('.,;()[]') for w in snippet.split()
                if w.strip('.,;()[]') and not _is_arabic(w)
            ]
            if len(words) >= 2:
                return ' '.join(words[:max_words])

    return ''


def _to_slug(text):
    """تحويل نص لـ URL slug نظيف (lowercase + hyphens فقط)."""
    text = text.lower().strip()
    text = re.sub(r"[''`]", '', text)          # إزالة apostrophes
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)  # إزالة رموز خاصة
    text = re.sub(r'\s+', '-', text)            # مسافات → شرطة
    text = re.sub(r'-{2,}', '-', text)          # شرطات متكررة
    return text.strip('-')


def _truncate_alt(text, max_chars=120):
    """
    اقتصاص Alt Text لـ <= 120 حرف (تحت حد 125 الموصى به من Shopify).
    يقطع عند آخر كلمة كاملة قبل الحد.
    """
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    return truncated[:last_space].rstrip(' -')


# ═══════════════════════════════════════════════════════════════
# 2b. بناء slug فريد (unique) بمراعاة المنتجات المكررة
# ═══════════════════════════════════════════════════════════════

# الكلمات اللي تفرّق بين نسخ مختلفة من نفس العطر — نحتفظ بها في الـ slug
VARIANT_MARKERS = {'edp', 'edt', 'parfum', 'extrait', 'collector',
                   '50ml', '100ml', '30ml', '15ml', '200ml'}


def build_unique_slug(handle, title=''):
    """
    يبني slug فريد مضمون — بيحتفظ بـ VARIANT_MARKERS لو موجودة في الـ handle.
    لو الـ slug مش كافي للتمييز، بيضيف 4 أحرف من hash الـ handle.
    """
    import hashlib
    parts = handle.split('-')
    clean = []
    for p in parts:
        if not p or _is_arabic(p) or re.match(r'^\d{4}$', p):
            continue
        pl = p.lower()
        if pl in VARIANT_MARKERS:
            clean.append(pl)
            continue
        if pl in FILENAME_NOISE:
            continue
        if re.match(r'^\d+$', p):
            continue
        clean.append(pl)

    slug = '-'.join(clean)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')

    if not slug and title:
        words = []
        for w in title.split():
            if _is_arabic(w): break
            wc = re.sub(r'[^a-z0-9]', '', w.lower())
            if wc and wc not in FILENAME_NOISE: words.append(wc)
        slug = '-'.join(words[:5])

    if not slug:
        slug = 'product'

    # طابع تمييز مختصر من الـ handle — يضمن التفريد النهائي
    # نستخدمه دائماً عشان نكون مطمنين 100%
    h4 = hashlib.md5(handle.encode()).hexdigest()[:4]
    return f"{slug}-{h4}"


# ═══════════════════════════════════════════════════════════════
# 3. استخراج البراند واسم العطر
# ═══════════════════════════════════════════════════════════════

def extract_brand_and_perfume(handle, title='', vendor=''):
    """
    استخراج اسم البراند واسم العطر.

    الأولوية:
      1. Vendor (من شوبيفاي — أدق مصدر، مملوء 100%)
      2. KNOWN_BRANDS dictionary
      3. نمط "by BrandName" في العنوان
      4. أول كلمة إنجليزية من العنوان
      5. أول كلمة من Handle (fallback أخير)

    أمثلة مع Vendor:
      vendor="Essential Parfums", title="Bois Impérial..."  → (Essential Parfums, Bois Imperial)
      vendor="Creed", title="CREED Himalaya..."            → (Creed, Himalaya)
      vendor="Lorenzo Pazzaglia", title="Speachless by..."  → (Lorenzo Pazzaglia, Speachless)

    Returns:
        (brand: str, perfume_name: str) — title-cased
    """
    brand = ''
    perfume_parts = []

    # ── استخراج كلمات إنجليزية من العنوان ──
    english_words = []
    if title:
        title_clean = re.sub(r'\.(?=[A-Za-z])', ' ', title)
        title_clean = re.sub(r'\.+', ' ', title_clean).strip()
        for word in title_clean.split():
            if _is_arabic(word):
                break
            clean = re.sub(r'[^\w\'\-]', '', word).strip("'-")
            if clean:
                english_words.append(clean)

    # حذف كلمات ضوضاء العنوان
    filtered = [
        w for w in english_words
        if w.lower() not in TITLE_NOISE
        and not re.match(r'^\d+$', w)
    ]

    # ═══════════════════════════════════════════
    # الأولوية 1: Vendor (أدق مصدر — من شوبيفاي)
    # ═══════════════════════════════════════════
    if vendor and vendor.strip() and not _is_arabic(vendor.strip()):
        brand = vendor.strip()
        # استخراج اسم العطر = العنوان بدون اسم البراند
        brand_words = brand.lower().split()
        remaining = []
        skip_count = 0
        for w in filtered:
            if skip_count < len(brand_words) and w.lower() == brand_words[skip_count]:
                skip_count += 1
                continue
            remaining.append(w)
        perfume_parts = remaining

    # ═══════════════════════════════════════════
    # الأولوية 2: KNOWN_BRANDS dictionary
    # ═══════════════════════════════════════════
    elif filtered:
        matched_brand = ''
        matched_len = 0
        for n in range(min(4, len(filtered)), 0, -1):
            candidate = ''.join(w.lower() for w in filtered[:n])
            if candidate in KNOWN_BRANDS:
                matched_brand = KNOWN_BRANDS[candidate]
                matched_len = n
                break
        if matched_brand:
            brand = matched_brand
            perfume_parts = filtered[matched_len:]

        # الأولوية 3: نمط "by BrandName"
        elif 'by' in [w.lower() for w in english_words]:
            lower_eng = [w.lower() for w in english_words]
            by_idx = lower_eng.index('by')
            before = [w for w in english_words[:by_idx]
                      if w.lower() not in TITLE_NOISE
                      and not re.match(r'^\d+$', w)]
            after = [w for w in english_words[by_idx + 1:]
                     if w.lower() not in TITLE_NOISE
                     and not re.match(r'^\d+$', w)]
            if before and after:
                brand = ' '.join(after)
                perfume_parts = before
            else:
                brand = filtered[0]
                perfume_parts = filtered[1:]

        # الأولوية 4: أول كلمة من العنوان
        else:
            brand = filtered[0]
            perfume_parts = filtered[1:]

    # ═══════════════════════════════════════════
    # الأولوية 5: Fallback — Handle
    # ═══════════════════════════════════════════
    if not brand:
        handle_parts = [
            p for p in handle.split('-')
            if p and not _is_arabic(p)
            and p.lower() not in FILENAME_NOISE
            and not re.match(r'^\d+', p)
        ]
        if handle_parts:
            brand = handle_parts[0].title()
            perfume_parts = [p.title() for p in handle_parts[1:3]]

    brand = brand.strip()
    perfume = ' '.join(perfume_parts).strip() if perfume_parts else ''

    # ── تصحيح حالة التكرار: "Adam Adam" ──
    if perfume.lower() == brand.lower():
        perfume = ''

    # ── لو اسم العطر فاضي: استخرج من Handle ──
    if not perfume:
        slug_parts = [
            p for p in handle.split('-')
            if p and not _is_arabic(p)
            and p.lower() not in FILENAME_NOISE
            and not re.match(r'^\d+', p)
        ]
        brand_slug = re.sub(r'[^a-z0-9]', '', brand.lower())
        remaining = []
        skip = 0
        for p in slug_parts:
            p_clean = re.sub(r'[^a-z0-9]', '', p.lower())
            if skip == 0 and p_clean and brand_slug.startswith(p_clean):
                skip = 1
                continue
            remaining.append(p)
        if remaining:
            perfume = ' '.join(p.title() for p in remaining[:4])

    # ── Defaults ──
    if not brand:
        brand = 'Perfume'

    # Title case
    if brand == brand.upper() or brand == brand.lower():
        brand = brand.title()
    if perfume and (perfume == perfume.upper() or perfume == perfume.lower()):
        perfume = perfume.title()

    return brand.strip(), perfume.strip()


# ═══════════════════════════════════════════════════════════════
# 4. تنظيف Handle لـ filename slug
# ═══════════════════════════════════════════════════════════════

def clean_handle_for_seo(handle, title=''):
    """
    تنظيف Handle شوبيفاي لاستخدامه في اسم الملف.
    يُزيل: العربي، كلمات الضوضاء، أرقام مجردة، UUIDs.
    يرجع slug إنجليزي نظيف بشرطات.
    """
    parts = handle.split('-')
    clean = []
    for p in parts:
        if not p:
            continue
        if _is_arabic(p):
            continue
        if p.lower() in FILENAME_NOISE:
            continue
        if re.match(r'^\d+$', p):
            continue
        if re.match(r'^\d+ml$', p.lower()):
            continue
        # UUID/hash طويل
        if len(p) > 25 and re.match(r'^[a-f0-9]+$', p.lower()):
            continue
        clean.append(p.lower())

    slug = '-'.join(clean)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-{2,}', '-', slug).strip('-')

    # Fallback من Title
    if not slug and title:
        words = []
        for w in title.split():
            if _is_arabic(w):
                break
            w_clean = re.sub(r'[^a-z0-9]', '', w.lower())
            if w_clean and w_clean not in FILENAME_NOISE:
                words.append(w_clean)
        slug = '-'.join(words[:5])

    return slug or 'product'


# ═══════════════════════════════════════════════════════════════
# 5. توليد اسم الملف SEO
# ═══════════════════════════════════════════════════════════════

def generate_seo_filename(clean_slug, position, total_images,
                          seo_desc_override=''):
    """
    توليد اسم ملف Shopify SEO-friendly.

    الصيغة: {slug}-{descriptor}.webp
    - كل شيء lowercase
    - شرطات بين الكلمات
    - بدون مسافات أو رموز أو UUID

    Args:
        clean_slug       : الـ slug النظيف من clean_handle_for_seo()
        position         : ترتيب الصورة (1-based)
        total_images     : إجمالي صور المنتج
        seo_desc_override: وصف يدوي اختياري (يتجاهل التلقائي)
    """
    if seo_desc_override and seo_desc_override.strip():
        desc = _to_slug(seo_desc_override.strip())
    elif total_images == 1:
        desc = 'perfume-decant'
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

def generate_alt_text(brand, perfume_name, position, total_images,
                      metadata=None):
    """
    توليد Alt Text متوافق مع Shopify SEO 2026.

    القواعد:
      • < 125 حرف (نستهدف < 120 للأمان)
      • يبدأ بـ Brand + Perfume Name
      • يتضمن keyword طبيعي
      • لا يبدأ بـ "image of" أو "picture of"
      • جملة مختلفة لكل صورة
      • لا keyword stuffing

    Args:
        brand        : اسم البراند
        perfume_name : اسم العطر
        position     : ترتيب الصورة
        total_images : إجمالي الصور
        metadata     : dict: olfactory_family, scent, season,
                       target_gender, sizes, notes_snippet
    """
    metadata = metadata or {}

    brand = (brand or 'Perfume').strip()
    perfume = (perfume_name or '').strip()
    product = f'{brand} {perfume}'.strip() if perfume else brand

    # ── بيانات سياقية ──
    olfactory = metadata.get('olfactory_family', '') or ''
    scent = metadata.get('scent', '') or ''
    season = metadata.get('season', '') or ''
    gender = metadata.get('target_gender', '') or ''
    sizes = metadata.get('sizes', '') or ''
    notes = metadata.get('notes_snippet', '') or ''

    # وصف رائحة مختصر (أول 2 عائلات فقط)
    scent_desc = ''
    families = [
        f.strip() for f in (olfactory or scent).replace(';', ',').split(',')
        if f.strip() and not _is_arabic(f.strip())
    ]
    if families:
        scent_desc = ' and '.join(families[:2])

    # مقاسات مختصرة
    size_str = sizes if sizes else '5ml and 10ml'

    # جنس
    gender_map = {
        'unisex': 'unisex', 'men': 'for men', 'male': 'for men',
        'women': 'for women', 'female': 'for women',
    }
    gender_desc = gender_map.get(gender.lower().strip(), '')

    # ── بناء Alt Text حسب الـ position ──
    if total_images == 1:
        # صورة واحدة — أكثر ما يمكن من المعلومات
        parts = [f'{product} perfume decant {size_str}']
        if scent_desc:
            parts.append(f'{scent_desc} fragrance')
        if gender_desc and gender_desc != 'unisex':
            parts.append(gender_desc)
        alt = ' - '.join(parts)

    elif position == 1:
        # الصورة الرئيسية — البراند + العطر + المقاسات + الرائحة
        parts = [f'{product} decant {size_str}']
        if scent_desc:
            parts.append(f'{scent_desc} fragrance')
        if gender_desc and gender_desc != 'unisex':
            parts.append(gender_desc)
        alt = ' - '.join(parts)

    elif position == 2:
        # تفاصيل الرائحة — النوتات أو العائلة الشمية
        if notes:
            alt = f'{product} - {notes[:50].rstrip(",")} scent'
        elif scent_desc:
            alt = f'{product} - {scent_desc} fragrance'
        else:
            alt = f'{product} fragrance'

    elif position == 3:
        # المقاسات والتوفر
        alt = f'{product} - available in {size_str} decants'
        if gender_desc:
            alt += f' {gender_desc}'

    elif position == 4:
        # الموسم والجنس
        if season:
            alt = f'{product} - {season} fragrance'
        elif notes:
            alt = f'{product} scent profile - {notes[:40].rstrip(",")}'
        else:
            alt = f'{product} scent profile'
        if gender_desc:
            alt += f' {gender_desc}'

    else:
        alt = f'{product} perfume {position}'

    # ── ضمان < 125 حرف (Shopify limit) ──
    return _truncate_alt(alt, max_chars=120)


# ═══════════════════════════════════════════════════════════════
# 7. ضغط الصورة — متوافق مع Shopify 2026
# ═══════════════════════════════════════════════════════════════

def compress_image_seo(img_path, output_path,
                       target_min_kb=80, target_max_kb=200,
                       max_dimension=2048):
    """
    ضغط صورة لـ Shopify SEO 2026.

    المعايير:
      • الهدف: < 200 KB (Shopify يوصي < 250 KB للـ LCP)
      • الأبعاد: <= 2048px (Shopify يوصي 2048×2048 للـ master)
      • الصيغة: WebP دائماً
      • جودة تبدأ من 88 وتنزل تدريجياً

    Returns:
        dict: original_size, compressed_size, dimensions_before,
              dimensions_after, quality_used
    """
    original_size = os.path.getsize(img_path)
    target_max = target_max_kb * 1024

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with Image.open(img_path) as img:
        dimensions_before = img.size

        # تحويل وضع الألوان
        if img.mode == 'RGBA':
            alpha = img.getchannel('A')
            if alpha.getextrema() == (255, 255):
                img = img.convert('RGB')
            # else: نحافظ على RGBA (WebP يدعمها)
        elif img.mode == 'P':
            img = img.convert('RGBA')
        elif img.mode not in ('RGB', 'RGBA', 'L'):
            img = img.convert('RGB')

        # Resize لو أكبر من 2048px
        w, h = img.size
        if w > max_dimension or h > max_dimension:
            ratio = min(max_dimension / w, max_dimension / h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        dimensions_after = img.size
        quality_used = 88

        # محاولة بجودة 88 أولاً
        buffer = BytesIO()
        save_kwargs = {'format': 'WEBP', 'quality': 88, 'method': 4}
        if img.mode == 'RGBA':
            save_kwargs['lossless'] = False
        img.save(buffer, **save_kwargs)
        current_size = buffer.tell()

        if current_size <= target_max:
            quality_used = 88
        else:
            # تقليل الجودة تدريجياً: 85 → 80 → 75 → 70 → 65 → 55 → 45
            for q in [85, 80, 75, 70, 65, 55, 45]:
                buffer = BytesIO()
                img.save(buffer, format='WEBP', quality=q, method=4)
                current_size = buffer.tell()
                quality_used = q
                if current_size <= target_max:
                    break

            # لو لسه فوق الهدف → resize إضافي (5% في كل مرة)
            if current_size > target_max:
                w2, h2 = img.size
                for scale in [0.85, 0.70, 0.55]:
                    nw = max(int(w2 * scale), 400)
                    nh = max(int(h2 * scale), 400)
                    resized = img.resize((nw, nh), Image.LANCZOS)
                    buffer = BytesIO()
                    resized.save(buffer, format='WEBP',
                                 quality=quality_used, method=4)
                    current_size = buffer.tell()
                    if current_size <= target_max:
                        img = resized
                        dimensions_after = (nw, nh)
                        break

        # حفظ الملف النهائي
        img.save(output_path, format='WEBP', quality=quality_used,
                 method=4)

    compressed_size = os.path.getsize(output_path)
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'dimensions_before': dimensions_before,
        'dimensions_after': dimensions_after,
        'quality_used': quality_used,
    }


# ═══════════════════════════════════════════════════════════════
# 8. SEO Logger
# ═══════════════════════════════════════════════════════════════

class SEOLogger:
    """
    تسجيل تفاصيل تحسين SEO لكل صورة في ملف CSV للمراجعة.

    الأعمدة:
      Handle | Position | Old Filename | New Filename | Alt Text
      Alt Length | Size Before (KB) | Size After (KB)
      Dimensions Before | Dimensions After | Quality Used
    """

    HEADERS = [
        'Handle', 'Position', 'Old Filename', 'New Filename',
        'Alt Text', 'Alt Length',
        'Size Before (KB)', 'Size After (KB)',
        'Dimensions Before', 'Dimensions After', 'Quality Used',
    ]

    def __init__(self, log_path='seo_optimization_log.csv'):
        self.log_path = log_path
        self.entries = []

    def add_entry(self, handle, position, old_filename, new_filename,
                  alt_text, compress_stats=None):
        """إضافة سجل صورة واحدة."""
        entry = {
            'Handle': handle,
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
            if e['Alt Length'] and int(e['Alt Length']) > 125
        ]
        msg = f"{total} images processed, {len(with_comp)} compressed"
        if over_limit:
            msg += f" ⚠️ {len(over_limit)} alt texts > 125 chars"
        return msg
