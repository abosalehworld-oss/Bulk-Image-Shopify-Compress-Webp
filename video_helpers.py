#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Helper Functions — Bulk Image & Video SEO Tool
ضغط الفيديو لـ WEBM + تحسين SEO + استخراج Thumbnail

المعايير:
  • الصيغة: WEBM (VP9 codec) — أفضل ضغط للويب
  • الصوت: Opus codec — أعلى جودة بأقل حجم
  • الدقة: يُحافظ على الأصلية حتى 1080p
  • الجودة: CRF mode — يحافظ على الجودة بدون بكسلة
  • Thumbnail: WebP مضغوط تلقائياً من أول ثواني الفيديو
  • PageSpeed: متوافق مع معايير Google PageSpeed Insights
"""

import os
import re
import sys
import json
import shutil
import zipfile
import subprocess
import tempfile
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 1. فحص FFmpeg
# ═══════════════════════════════════════════════════════════════

# مجلد FFmpeg المحلي (بجوار السكريبت)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_FFMPEG_DIR = os.path.join(_SCRIPT_DIR, 'ffmpeg_bin')

# رابط تحميل FFmpeg portable (Windows 64-bit, gyan.dev — مصدر موثوق)
_FFMPEG_DOWNLOAD_URL = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'


def _get_local_ffmpeg_exe():
    """مسار ffmpeg.exe المحلي."""
    return os.path.join(_LOCAL_FFMPEG_DIR, 'ffmpeg.exe')


def _get_local_ffprobe_exe():
    """مسار ffprobe.exe المحلي."""
    return os.path.join(_LOCAL_FFMPEG_DIR, 'ffprobe.exe')


def check_ffmpeg():
    """
    التحقق من وجود FFmpeg — يبحث في:
    1. PATH النظام
    2. مجلد ffmpeg_bin/ المحلي (بجوار السكريبت)
    3. المسارات الشائعة على Windows
    
    Returns:
        bool: True لو FFmpeg موجود
    """
    # 1. PATH
    if shutil.which('ffmpeg'):
        return True
    
    # 2. المجلد المحلي
    if os.path.exists(_get_local_ffmpeg_exe()):
        return True
    
    # 3. مسارات شائعة
    if sys.platform == 'win32':
        for p in [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            os.path.expanduser(r'~\ffmpeg\bin\ffmpeg.exe'),
        ]:
            if os.path.exists(p):
                return True
    
    return False


def auto_install_ffmpeg(progress_callback=None):
    """
    تحميل وتثبيت FFmpeg تلقائياً (مرة واحدة فقط).
    
    يحمّل FFmpeg portable من gyan.dev ويحفظه في مجلد ffmpeg_bin/
    بجوار السكريبت. مش محتاج صلاحيات Admin.
    
    Args:
        progress_callback: callable(message) للتحديثات — اختياري
    
    Returns:
        bool: True لو التثبيت نجح
    """
    # لو موجود أصلاً — مش محتاج تحميل
    if check_ffmpeg():
        return True
    
    def _log(msg):
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    import urllib.request
    import io
    
    _log("[INFO] Downloading FFmpeg (first time only)...")
    
    try:
        os.makedirs(_LOCAL_FFMPEG_DIR, exist_ok=True)
        zip_path = os.path.join(_LOCAL_FFMPEG_DIR, 'ffmpeg_download.zip')
        
        # تحميل الملف
        _log("[INFO] Downloading from gyan.dev (~80 MB)...")
        urllib.request.urlretrieve(_FFMPEG_DOWNLOAD_URL, zip_path)
        
        _log("[INFO] Extracting FFmpeg...")
        
        # فك الضغط — نبحث عن ffmpeg.exe و ffprobe.exe
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                basename = os.path.basename(member).lower()
                if basename in ('ffmpeg.exe', 'ffprobe.exe'):
                    # استخراج الملف مباشرة لمجلد ffmpeg_bin/
                    target = os.path.join(_LOCAL_FFMPEG_DIR, basename)
                    with zf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
        
        # حذف الـ ZIP بعد الاستخراج (توفير مساحة)
        try:
            os.remove(zip_path)
        except OSError:
            pass
        
        # تحقق
        if os.path.exists(_get_local_ffmpeg_exe()):
            _log("[OK] FFmpeg installed successfully!")
            return True
        else:
            _log("[ERROR] FFmpeg extraction failed")
            return False
    
    except Exception as e:
        _log(f"[ERROR] FFmpeg download failed: {e}")
        # تنظيف
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception:
            pass
        return False


def _get_ffmpeg_path():
    """الحصول على مسار FFmpeg — يبحث في كل الأماكن."""
    # 1. PATH
    p = shutil.which('ffmpeg')
    if p:
        return p
    
    # 2. المجلد المحلي
    local = _get_local_ffmpeg_exe()
    if os.path.exists(local):
        return local
    
    # 3. مسارات شائعة
    if sys.platform == 'win32':
        for p in [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            os.path.expanduser(r'~\ffmpeg\bin\ffmpeg.exe'),
        ]:
            if os.path.exists(p):
                return p
    
    return 'ffmpeg'  # fallback


def _get_ffprobe_path():
    """الحصول على مسار FFprobe."""
    # 1. PATH
    p = shutil.which('ffprobe')
    if p:
        return p
    
    # 2. المجلد المحلي
    local = _get_local_ffprobe_exe()
    if os.path.exists(local):
        return local
    
    # 3. نفس مجلد ffmpeg
    ffmpeg = _get_ffmpeg_path()
    ffprobe = ffmpeg.replace('ffmpeg', 'ffprobe')
    if os.path.exists(ffprobe):
        return ffprobe
    
    return 'ffprobe'


# ═══════════════════════════════════════════════════════════════
# 2. معلومات الفيديو
# ═══════════════════════════════════════════════════════════════

def get_video_info(video_path):
    """
    استخراج معلومات الفيديو (المدة، الأبعاد، الحجم، الـ codec).
    
    Returns:
        dict: duration, width, height, fps, codec, has_audio, file_size
              أو None لو فشل
    """
    try:
        ffprobe = _get_ffprobe_path()
        cmd = [
            ffprobe, '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            str(video_path)
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        
        # البحث عن stream الفيديو
        video_stream = None
        has_audio = False
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and not video_stream:
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                has_audio = True
        
        if not video_stream:
            return None
        
        # استخراج FPS
        fps_str = video_stream.get('r_frame_rate', '30/1')
        try:
            num, den = fps_str.split('/')
            fps = round(float(num) / float(den), 2)
        except (ValueError, ZeroDivisionError):
            fps = 30.0
        
        # المدة
        duration = float(data.get('format', {}).get('duration', 0))
        if duration == 0:
            duration = float(video_stream.get('duration', 0))
        
        # استخراج rotation metadata
        # الفيديوهات من الموبايل/تيك توك/سوشيال ميديا بتخزن rotation tag
        # مثل EXIF Orientation في الصور — لازم نتعامل معاه صح
        rotation = 0
        # طريقة 1: من side_data_list (MP4/MOV الحديثة)
        side_data = video_stream.get('side_data_list', [])
        for sd in side_data:
            if 'rotation' in sd:
                rotation = int(sd.get('rotation', 0))
            elif sd.get('side_data_type') == 'Display Matrix':
                rotation = int(sd.get('rotation', 0))
                
        # طريقة 2: من tags في الـ stream أو الـ format (MP4/MOV)
        if rotation == 0:
            stream_tags = video_stream.get('tags', {})
            format_tags = data.get('format', {}).get('tags', {})
            rotate_tag = stream_tags.get('rotate') or stream_tags.get('ROTATE') or format_tags.get('rotate') or format_tags.get('ROTATE') or '0'
            try:
                rotation = int(float(rotate_tag))
            except (ValueError, TypeError):
                rotation = 0
        
        # الأبعاد المخزنة (قبل الدوران)
        stored_w = int(video_stream.get('width', 0))
        stored_h = int(video_stream.get('height', 0))
        
        # الأبعاد الحقيقية بعد تطبيق الدوران
        # لو الفيديو متصور بالموبايل عمودي (portrait) وعنده rotation 90 أو 270
        # فالأبعاد المخزنة معكوسة — العرض والطول مقلوبين
        if abs(rotation) in (90, 270):
            display_w = stored_h
            display_h = stored_w
        else:
            display_w = stored_w
            display_h = stored_h
        
        return {
            'duration': duration,
            'width': display_w,           # العرض الحقيقي (بعد الدوران)
            'height': display_h,          # الطول الحقيقي (بعد الدوران)
            'stored_width': stored_w,     # العرض المخزن (قبل الدوران)
            'stored_height': stored_h,    # الطول المخزن (قبل الدوران)
            'rotation': rotation,         # زاوية الدوران
            'fps': fps,
            'codec': video_stream.get('codec_name', 'unknown'),
            'has_audio': has_audio,
            'file_size': os.path.getsize(video_path),
        }
    
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# 3. ضغط الفيديو — WEBM (VP9)
# ═══════════════════════════════════════════════════════════════

def compress_video_seo(video_path, output_path, max_dimension=1080,
                       target_quality='balanced'):
    """
    ضغط فيديو لـ WEBM (VP9 + Opus) متوافق مع Google PageSpeed.
    
    المعايير:
      • VP9 codec — أفضل ضغط للويب (يدعمه كل المتصفحات)
      • CRF mode — جودة ثابتة بدون بكسلة
      • Opus audio — أعلى جودة صوت بأقل حجم
      • الدقة: <= 1080p (تصغير تلقائي لو أكبر)
      • FPS: <= 30 (للويب مش محتاج أكثر)
    
    Args:
        video_path: مسار الفيديو المصدر
        output_path: مسار الفيديو المضغوط (.webm)
        max_dimension: أكبر بُعد مسموح (افتراضي 1080)
        target_quality: 'high' (CRF 28), 'balanced' (CRF 32), 'small' (CRF 36)
    
    Returns:
        dict: original_size, compressed_size, duration, dimensions_before,
              dimensions_after, crf_used
    """
    original_size = os.path.getsize(video_path)
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # معلومات الفيديو الأصلي
    info = get_video_info(video_path)
    if not info:
        raise ValueError(f"Could not read video info: {video_path}")
    
    dimensions_before = (info['width'], info['height'])
    
    # ── اختيار CRF حسب الجودة المطلوبة ──
    # CRF أقل = جودة أعلى + حجم أكبر
    # CRF 28-32 = توازن ممتاز للويب بدون بكسلة
    crf_map = {
        'high': 28,      # جودة عالية — حجم أكبر شوية
        'balanced': 31,   # توازن مثالي — أفضل لـ PageSpeed
        'small': 35,      # حجم صغير — مقبول للفيديوهات الطويلة
    }
    crf = crf_map.get(target_quality, 31)
    
    # ── تحديد الدقة مع مراعاة الدوران ──
    # نستخدم الأبعاد الحقيقية (display) مش المخزنة
    w, h = info['width'], info['height']  # دي الأبعاد بعد الدوران
    rotation = info.get('rotation', 0)
    
    # بناء قائمة الفلاتر
    vfilters = []
    
    # تصحيح الدوران — مهم جداً لفيديوهات الموبايل/تيك توك/سوشيال ميديا
    # FFmpeg عند التحويل لـ WEBM ممكن يتجاهل rotation metadata
    # فلازم نطبقه يدوياً عشان الفيديو ميطلعش مقلوب
    if abs(rotation) == 90:
        vfilters.append('transpose=1')  # 90° CW
    elif abs(rotation) == 270 or rotation == -90:
        vfilters.append('transpose=2')  # 90° CCW (270° CW)
    elif abs(rotation) == 180:
        vfilters.append('transpose=1,transpose=1')  # 180°
    
    # تصغير لو أكبر من max_dimension
    if w > max_dimension or h > max_dimension:
        if w >= h:
            vfilters.append(f"scale={max_dimension}:-2")
        else:
            vfilters.append(f"scale=-2:{max_dimension}")
    
    # ── تحديد FPS ──
    fps = min(info['fps'], 30)
    
    # ── بناء أمر FFmpeg ──
    ffmpeg = _get_ffmpeg_path()
    cmd = [
        ffmpeg,
        '-noautorotate',                 # منع FFmpeg من الدوران التلقائي — إحنا هنعمله يدوي
        '-i', str(video_path),
        '-c:v', 'libvpx-vp9',           # VP9 codec
        '-crf', str(crf),                # Constant Rate Factor
        '-b:v', '0',                     # CRF mode
        '-r', str(int(fps)),             # FPS
        '-deadline', 'good',             # سرعة الترميز
        '-cpu-used', '2',                # سرعة CPU
        '-row-mt', '1',                  # Multi-threading
        '-threads', '4',                 # عدد الخيوط
    ]
    
    # تطبيق الفلاتر (دوران + تصغير)
    if vfilters:
        cmd.extend(['-vf', ','.join(vfilters)])
    
    # الصوت
    if info['has_audio']:
        cmd.extend([
            '-c:a', 'libopus',           # Opus codec
            '-b:a', '128k',              # 128kbps
            '-ac', '2',                  # Stereo
        ])
    else:
        cmd.extend(['-an'])              # بدون صوت
    
    # إزالة rotation metadata من الملف الناتج (عشان احنا طبقناه يدوي)
    cmd.extend([
        '-metadata:s:v', 'rotate=0',
        '-y',                            # overwrite
        str(output_path)
    ])
    
    # ── تنفيذ ──
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr[-500:]}")
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("Video compression timed out (>10 minutes)")
    
    # ── النتيجة ──
    compressed_size = os.path.getsize(output_path)
    
    # معلومات الفيديو المضغوط
    out_info = get_video_info(output_path)
    dimensions_after = (out_info['width'], out_info['height']) if out_info else dimensions_before
    
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'duration': info['duration'],
        'dimensions_before': dimensions_before,
        'dimensions_after': dimensions_after,
        'crf_used': crf,
        'fps': fps,
        'has_audio': info['has_audio'],
    }


# ═══════════════════════════════════════════════════════════════
# 4. استخراج Thumbnail — WebP مضغوط
# ═══════════════════════════════════════════════════════════════

def generate_video_thumbnail(video_path, output_path, timestamp=1.0,
                             max_dimension=1280, quality=85):
    """
    استخراج صورة مصغرة (Thumbnail/Poster) من الفيديو وحفظها كـ WebP مضغوط.
    
    Args:
        video_path: مسار الفيديو
        output_path: مسار الصورة المصغرة (.webp)
        timestamp: الثانية المراد أخذ الصورة منها (افتراضي: 1.0)
        max_dimension: أكبر بُعد للصورة (افتراضي: 1280)
        quality: جودة WebP (افتراضي: 85)
    
    Returns:
        dict: thumbnail_path, thumbnail_size, dimensions
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # تأكد إن الـ timestamp مش أكبر من مدة الفيديو
    info = get_video_info(video_path)
    if info and info['duration'] > 0:
        timestamp = min(timestamp, info['duration'] * 0.25)  # أول 25% من الفيديو
        timestamp = max(timestamp, 0.1)  # على الأقل 0.1 ثانية
    
    # ── استخراج الفريم بـ FFmpeg ──
    ffmpeg = _get_ffmpeg_path()
    
    # نصدّر فريم مؤقت كـ PNG ثم نضغطه كـ WebP
    temp_png = output_path + '.tmp.png'
    
    # بناء فلاتر (دوران + تصغير)
    w = info['width'] if info else 1920
    h = info['height'] if info else 1080
    rotation = info.get('rotation', 0) if info else 0
    
    vfilters = []
    
    # تصحيح الدوران (نفس منطق compress_video_seo)
    if abs(rotation) == 90:
        vfilters.append('transpose=1')
    elif abs(rotation) == 270 or rotation == -90:
        vfilters.append('transpose=2')
    elif abs(rotation) == 180:
        vfilters.append('transpose=1,transpose=1')
    
    # تصغير لو أكبر من max_dimension
    if w > max_dimension or h > max_dimension:
        if w >= h:
            vfilters.append(f"scale={max_dimension}:-2")
        else:
            vfilters.append(f"scale=-2:{max_dimension}")
    
    cmd = [
        ffmpeg,
        '-noautorotate',               # نتحكم بالدوران يدوياً
        '-ss', str(timestamp),         # seek قبل input (أسرع)
        '-i', str(video_path),
        '-frames:v', '1',              # فريم واحد فقط
        '-q:v', '2',                   # جودة عالية
    ]
    
    if vfilters:
        cmd.extend(['-vf', ','.join(vfilters)])
    
    cmd.extend(['-y', temp_png])
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        if result.returncode != 0 or not os.path.exists(temp_png):
            raise RuntimeError(f"Failed to extract thumbnail: {result.stderr[-300:]}")
        
        # ── ضغط كـ WebP ──
        try:
            from PIL import Image, ImageOps
            with Image.open(temp_png) as img:
                # تصحيح EXIF (احتياطي)
                img = ImageOps.exif_transpose(img)
                
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                
                dimensions = img.size
                img.save(output_path, 'WEBP', quality=quality, method=4)
        except ImportError:
            # fallback: حفظ PNG كما هو
            import shutil
            shutil.move(temp_png, output_path)
            dimensions = (w, h)
        
        thumbnail_size = os.path.getsize(output_path)
        
        return {
            'thumbnail_path': output_path,
            'thumbnail_size': thumbnail_size,
            'dimensions': dimensions,
        }
    
    finally:
        # تنظيف الملف المؤقت
        if os.path.exists(temp_png):
            try:
                os.remove(temp_png)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════
# 5. توليد اسم ملف SEO للفيديو
# ═══════════════════════════════════════════════════════════════

# أوصاف عامة للفيديو
VIDEO_DESCRIPTORS = {
    1: 'product-video',
    2: 'demo-video',
    3: 'detail-video',
    4: 'showcase-video',
}

# أوصاف Thumbnail
THUMBNAIL_DESCRIPTORS = {
    1: 'video-poster',
    2: 'video-thumbnail',
    3: 'video-cover',
}


def _to_slug(text):
    """تحويل نص لـ URL slug نظيف."""
    text = text.lower().strip()
    text = re.sub(r"[''`]", '', text)
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-{2,}', '-', text)
    return text.strip('-')


def generate_video_seo_filename(clean_slug, position, total_videos,
                                seo_desc_override=''):
    """
    توليد اسم ملف SEO-friendly للفيديو.
    
    الصيغة: {slug}-{descriptor}.webm
    
    Args:
        clean_slug: الـ slug النظيف (من clean_handle_for_seo)
        position: ترتيب الفيديو
        total_videos: إجمالي فيديوهات المنتج
        seo_desc_override: وصف يدوي اختياري
    
    Returns:
        str: اسم الملف بصيغة .webm
    """
    if seo_desc_override and seo_desc_override.strip():
        desc = _to_slug(seo_desc_override.strip())
    elif total_videos == 1:
        desc = 'product-video'
    elif position in VIDEO_DESCRIPTORS:
        desc = VIDEO_DESCRIPTORS[position]
    else:
        desc = f'video-{position}'
    
    filename = f'{clean_slug}-{desc}.webm'
    filename = re.sub(r'-{2,}', '-', filename)
    return filename.lower()


def generate_video_thumbnail_filename(clean_slug, position):
    """
    توليد اسم ملف SEO للـ Thumbnail.
    
    الصيغة: {slug}-{descriptor}.webp
    """
    desc = THUMBNAIL_DESCRIPTORS.get(position, 'video-poster')
    filename = f'{clean_slug}-{desc}.webp'
    filename = re.sub(r'-{2,}', '-', filename)
    return filename.lower()


# ═══════════════════════════════════════════════════════════════
# 6. توليد Alt Text للفيديو
# ═══════════════════════════════════════════════════════════════

def generate_video_alt_text(brand, product_name, position, total_videos,
                            metadata=None):
    """
    توليد Alt Text/Title للفيديو — متوافق مع SEO.
    
    القواعد:
      • < 125 حرف
      • يبدأ بـ Brand + Product Name
      • يتضمن كلمة "video"
    
    Args:
        brand: اسم البراند
        product_name: اسم المنتج
        position: ترتيب الفيديو
        total_videos: إجمالي الفيديوهات
        metadata: dict إضافي
    
    Returns:
        str: Alt text
    """
    metadata = metadata or {}
    
    brand = (brand or '').strip()
    product_name = (product_name or '').strip()
    product = f'{brand} {product_name}'.strip() if product_name else brand
    if not product:
        product = 'Product'
    
    if total_videos == 1:
        alt = f'{product} - product video showcase'
    elif position == 1:
        alt = f'{product} - official product video'
    elif position == 2:
        alt = f'{product} - product demo and review'
    elif position == 3:
        alt = f'{product} - detailed product video'
    else:
        alt = f'{product} - product video {position}'
    
    # اقتصاص لـ 120 حرف
    if len(alt) > 120:
        alt = alt[:120]
        last_space = alt.rfind(' ')
        if last_space > 0:
            alt = alt[:last_space].rstrip(' -')
    
    return alt


# ═══════════════════════════════════════════════════════════════
# 7. ثوابت ودوال مساعدة
# ═══════════════════════════════════════════════════════════════

# امتدادات الفيديو المدعومة
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v',
                    '.wmv', '.flv', '.3gp', '.mts', '.ts')

# امتدادات الصور (للتصنيف)
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif')


def is_video_file(filepath):
    """هل الملف ده فيديو؟"""
    return os.path.splitext(filepath)[1].lower() in VIDEO_EXTENSIONS


def is_image_file(filepath):
    """هل الملف ده صورة؟"""
    return os.path.splitext(filepath)[1].lower() in IMAGE_EXTENSIONS


def classify_media_files(file_list):
    """
    تصنيف قائمة ملفات إلى صور وفيديوهات.
    
    Args:
        file_list: قائمة مسارات الملفات
    
    Returns:
        dict: {'images': [...], 'videos': [...], 'other': [...]}
    """
    result = {'images': [], 'videos': [], 'other': []}
    for f in file_list:
        if is_image_file(f):
            result['images'].append(f)
        elif is_video_file(f):
            result['videos'].append(f)
        else:
            result['other'].append(f)
    return result


def format_duration(seconds):
    """تنسيق المدة بالدقائق والثواني."""
    if seconds <= 0:
        return "0s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def format_size(size_bytes):
    """تنسيق الحجم بشكل مقروء."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
