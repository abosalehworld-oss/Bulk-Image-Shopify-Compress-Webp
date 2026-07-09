# 🛒 Shopify Bulk Image Compressor & SEO Optimizer

[اللغة العربية بالأسفل ⬇️](#-النسخة-العربية)

## 📋 Overview
An advanced Python GUI tool specifically designed for Shopify store owners and SEO specialists. This tool automates the entire image optimization pipeline, saving hundreds of hours of manual work:

1. **📥 Bulk Downloading**: Reads your exported Shopify CSV and downloads all store images.
2. **🧠 SEO Intelligence (Auto-renaming & Alt-Text)**: It analyzes product names, removes noise words (e.g., edp, ml, decant), and generates 100% SEO-friendly filenames (hyphenated, lowercase). It also automatically crafts highly descriptive Alt Text.
3. **🗜️ WebP Compression**: Converts all image formats to WebP and smartly resizes massive images (down to 2000px). It hits the "golden size" (80-150KB) to dramatically improve your Largest Contentful Paint (LCP) performance without noticeable quality loss.
4. **📦 Direct Images & ZIP/RAR Support**: Don't have a CSV? No problem. Feed the tool single images or entire ZIP/RAR archives. It will automatically extract them, use the folder/file names as product titles, and apply the exact same SEO and compression logic.
5. **📄 Ready-to-Import CSV**: Generates a `products_seo_optimized.csv` file that you can directly import back into Shopify to update your store with the new WebP images and optimized Alt Texts.

---

## 🖥️ How to Run

### Quick Start (Windows):
Double-click on `تشغيل_الأداة.bat` to launch the GUI instantly! ✅

### Via Command Line:
```bash
python shopify_gui.py
```

---

## ⚙️ Requirements (One-time setup)

1. **Install Python**: Download from [python.org](https://www.python.org/downloads/) (Make sure to check "Add Python to PATH" during installation).
2. **Install Dependencies**: Open Command Prompt and run:
```bash
pip install requests Pillow tqdm rarfile
```
*(Note: To extract RAR files, you must have UnRAR or WinRAR installed on your system. ZIP extraction is natively supported).*

---

## 🎯 GUI Guide

### 1: Operation Mode
- **📥🗜️ Download & Compress (Default)**: Downloads images from Shopify and compresses them with SEO rules.
- **📥 Download Only**: Only downloads the images if you want to compress them externally.
- **🗜️ Compress Only**: Apply SEO rules and compress images you already have on your machine.

### 2: Input Source
- **Shopify CSV**: Use this if you exported your store products to a CSV file.
- **Direct Images / Archive (ZIP/RAR)**: Use this to process raw image files or archives directly.

### 3: Save Locations
Choose the folders where downloaded and optimized (compressed) images will be saved.

### 4: Settings
- **Quality**: Adjust WebP compression quality (85% recommended).
- **Workers**: Number of parallel downloads/processes (10 recommended).

---

## 📁 Core Project Files
- `shopify_gui.py`: The interactive GUI.
- `shopify_image_downloader.py`: The core engine for downloading, processing, and exporting.
- `seo_helpers.py`: The "brain" behind the SEO rules, filename filtering, and Alt-Text generation.
- `PROJECT_ARCHITECTURE.md`: Technical documentation for developers and AI assistants.

***

# 🛒 النسخة العربية (Arabic Version)

## 📋 نظرة عامة
أداة بايثون بواجهة رسومية متطورة مصممة خصيصاً لخبراء الـ SEO وأصحاب متاجر شوبيفاي. تقوم الأداة بأتمتة مهام تحسين الصور بالكامل لتوفير مئات الساعات من العمل اليدوي:

1. **📥 تحميل الصور بالجملة**: من خلال قراءة ملف CSV المصدر من شوبيفاي وتحميل جميع صور المتجر.
2. **🧠 ذكاء الـ SEO (تسمية احترافية و Alt-Text)**: الأداة تُحلل أسماء المنتجات، تحذف الكلمات المزعجة (Noise words مثل edp, ml)، وتولد مسميات ملفات متوافقة 100% مع الـ SEO. كما تستخرج نصوص بديلة (Alt Text) جذابة ومناسبة.
3. **🗜️ ضغط وتحويل إلى WebP**: تحويل جميع صيغ الصور إلى WebP، وتصغير الأبعاد الكبيرة جداً. لتصل إلى الحجم المثالي (بين 80-150 كيلوبايت) لرفع تقييم سرعة تحميل موقعك (LCP).
4. **📦 دعم الصور الفردية وملفات الـ (ZIP/RAR)**: تتيح لك إدخال صور فردية أو رفع ملفات مضغوطة بالكامل لتقوم الأداة بفك ضغطها وتطبيق جميع قواعد الـ SEO عليها بدون الحاجة لملف CSV!
5. **📄 تصدير CSV جاهز للرفع**: يتم توليد ملف `products_seo_optimized.csv` جديد وجاهز للإدخال (Import) مباشرة في متجرك لتحديث الصور والـ Alt Text.

---

## 🖥️ تشغيل الأداة

### الطريقة الأسهل:
**دوبل كليك على ملف `تشغيل_الأداة.bat`** ← الواجهة هتفتح فورًا ✅

### أو من سطر الأوامر:
```bash
python shopify_gui.py
```

---

## ⚙️ متطلبات التشغيل (مرة واحدة بس)

### 1. تثبيت Python
1. حمّل Python من [python.org/downloads](https://www.python.org/downloads/)
2. **✅ مهم جدًا:** ضع علامة ✅ على **"Add Python to PATH"** أثناء التثبيت

### 2. تثبيت المكتبات
افتح Command Prompt واكتب:
```bash
pip install requests Pillow tqdm rarfile
```
*(ملاحظة: لفك ضغط ملفات الـ RAR، ستحتاج لوجود برنامج UnRAR أو WinRAR على نظامك للتوافق التام)*

---

## 🎯 الواجهة الرسومية - شرح مبسط

### 🎯 اختيار العملية (Mode)
- **📥🗜️ تحميل + ضغط**: الخيار الافتراضي - يحمّل الصور من شوبيفاي ويقوم بضغطها وتحسين الـ SEO.
- **📥 تحميل فقط**: عايز تحمّل الصور وتضغطها بنفسك ببرامج خارجية.
- **🗜️ ضغط فقط**: عندك صور على جهازك وعايز تطبق عليها الـ SEO وتضغطها.

### 📄 مصدر الإدخال والملفات (Input Source)
1. **Shopify CSV**: اختر هذا الوضع إذا كان لديك ملف `products.csv` من شوبيفاي.
2. **Direct Images / Archive (ZIP/RAR)**: اختر هذا الوضع لضغط صور مفردة أو ملف مضغوط.

### 📁 أماكن الحفظ والإعدادات
- اختر مسار التخزين للصور المحملة وللصور بعد ضغطها.
- يُنصح بجودة (Quality) **85%** وبعدد عمليات (Workers) **10**.

---

> 🛠️ **تم تصميم وتطوير هذه الأداة للوصول إلى المراتب الأولى في نتائج محركات البحث لصور شوبيفاي** 🚀
