# 📖 دليل المستخدم الكامل — أداة تحسين صور المنتجات
## Bulk Image SEO Tool — Complete User Guide

> **للمبتدئين** — اتبع الخطوات بالترتيب ← ✅

---

## 🚀 قبل أي شيء — التثبيت (مرة واحدة فقط)

### الخطوة 1: تثبيت Python

1. افتح الرابط: **https://www.python.org/downloads/**
2. اضغط **"Download Python"** الزر الكبير
3. شغّل ملف التثبيت
4. ✅ **مهم جداً:** ضع علامة على **"Add Python to PATH"** قبل ما تضغط Install
5. اضغط **Install Now**

> 💡 للتأكد: افتح Command Prompt واكتب `py --version` — لازم يطلع رقم إصدار

---

### الخطوة 2: تثبيت المكتبات

1. افتح **Command Prompt** (ابحث عنه في ابدأ)
2. اكتب الأمر ده واضغط Enter:

```
pip install requests Pillow tqdm rarfile
```

3. انتظر لحد ما يخلص (دقيقة تقريباً)
4. ✅ خلص — مش هتعمله تاني

---

### الخطوة 3: تشغيل الأداة

**الطريقة السهلة:**
> 🖱️ دوبل كليك على ملف `تشغيل_الأداة.bat`

**أو من Command Prompt:**
```
py shopify_gui.py
```

---
---

# 🛒 قسم أول: شوبيفاي

---

## 📥 السيناريو 1: عندي ملف CSV من شوبيفاي وعايز أحمّل الصور وأضغطها

**الهدف:** تحميل كل صور المنتجات من شوبيفاي + ضغطها + تسمية SEO

### الخطوات:

**① تصدير CSV من شوبيفاي**
1. افتح متجرك على Shopify
2. اذهب لـ **Products** (المنتجات)
3. اضغط **Export** (تصدير)
4. اختر **All products** → **CSV for Excel**
5. احفظ الملف على جهازك

**② شغّل الأداة**
1. شغّل الأداة → اضغط تبويب **🛒 Shopify**
2. في **"Choose Mode"** اختر: `📥🗜️ Download + Compress` (تحميل + ضغط)
3. في **"Input Source"** اختر: `Shopify CSV`

**③ اختر الملفات**
- **Shopify CSV:** اضغط "Choose CSV" واختر ملف الـ CSV اللي صدّرته
- **Download Folder:** اضغط "Choose" واختر مجلد لحفظ الصور المحملة (مثال: `Desktop/downloaded`)
- **Compress Folder:** اضغط "Choose" واختر مجلد للصور المضغوطة (مثال: `Desktop/optimized`)

**④ الإعدادات (اتركها كما هي للمبتدئين)**
- Quality: **85%** ✅
- Workers: **10** ✅

**⑤ اضغط START**
- راقب السجل (Log) — هتشوف التقدم
- انتظر لحد ما يكتب: **"DONE"** ✅

**⑥ النتائج**
افتح مجلد الـ Compress وهتلاقي:
```
📁 compressed_images/
├── 📁 product-handle-1/
│   ├── brand-name-product-1-perfume-decant.webp   ← صورة مضغوطة + اسم SEO
│   ├── brand-name-product-1-fragrance-detail.webp
│   └── ...
├── 📁 product-handle-2/
└── ...
📄 products_seo_optimized.csv    ← للاستيراد في شوبيفاي
📄 seo_optimization_log.csv      ← سجل التحسينات
📄 report.txt                    ← تقرير
```

---

## 🗜️ السيناريو 2: عندي صور على جهازي (بدون CSV شوبيفاي)

**الهدف:** ضغط صور موجودة على جهازك + تسمية SEO

### الخطوات:

**① رتّب صورك في مجلدات**

```
📁 my_products/
├── 📁 tom-ford-tobacco-vanille/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
├── 📁 xerjoff-naxos/
│   ├── img1.png
│   └── img2.png
```

> 💡 اسم المجلد هو اللي هيبني اسم الملف SEO منه

**② شغّل الأداة**
1. اضغط تبويب **🛒 Shopify**
2. في **"Choose Mode"** اختر: `🗜️ Compress Only`
3. في **"Input Source"** اختر: `Direct Images / Archive (ZIP/RAR)`

**③ اختر الملفات**
- اضغط **"Choose Images/ZIP"** واختر صورك أو ملف ZIP يحتوي عليها

**④ اضغط START وانتظر DONE ✅**

---

## 📤 السيناريو 3: رفع الصور المحسّنة على شوبيفاي

**بعد ما تخلص الضغط والتسمية:**

### طريقة 1: استيراد CSV (الأسهل)
1. افتح شوبيفاي → **Products** → **Import**
2. اختر ملف `products_seo_optimized.csv`
3. ✅ شوبيفاي هيحدّث صور كل المنتجات تلقائياً

### طريقة 2: رفع يدوي
1. اذهب لكل منتج على شوبيفاي
2. احذف الصور القديمة
3. ارفع الصور الجديدة (WebP) من مجلد `compressed_images`

---
---

# 🌐 قسم ثاني: ووردبريس / WooCommerce

> ⚠️ **وضع ووردبريس: كل شيء على جهازك — لا رفع تلقائي**
> المستخدم يرفع الصور يدوياً لمكتبة الميديا للأمان الكامل

---

## 📦 السيناريو 1: عندي ملف CSV من WooCommerce

**الهدف:** ضغط صور المنتجات + تسمية SEO + تجهيز Alt Text للرفع اليدوي

### الخطوة 1: تصدير CSV من WooCommerce

1. افتح لوحة التحكم WordPress
2. اذهب لـ **WooCommerce** → **Products** → **Export**
3. اضغط **"Generate the CSV"**
4. احفظ الملف على جهازك (`products_export.csv`)

### الخطوة 2: ضع صور المنتجات في مجلد

رتّب الصور هكذا (مجلد لكل منتج):
```
📁 product_images/
├── 📁 iphone-15-pro-max/   ← اسم المجلد = SKU أو اسم المنتج
│   ├── front.jpg
│   ├── back.jpg
│   └── detail.png
├── 📁 samsung-galaxy-s24/
│   └── main.jpg
```

### الخطوة 3: شغّل الأداة

1. شغّل الأداة → اضغط تبويب **🌐 WordPress**
2. في **"Input Source"** اختر: `WooCommerce CSV`
3. اضغط **"Choose WooCommerce CSV"** واختر ملف الـ CSV
4. في **"Images Folder"** اختر مجلد صورك (`product_images`)
5. في **"Compressed Folder"** اختر مجلد للحفظ (مثال: `Desktop/wp_ready`)
6. اضغط **START** وانتظر **"Done! ✅"**

### الخطوة 4: مراجعة النتائج

```
📁 wp_ready/
├── 📁 iphone-15-pro-max/
│   ├── iphone-15-pro-max-abc1-main-product-image.webp
│   ├── iphone-15-pro-max-abc1-detail-view.webp
│   └── iphone-15-pro-max-abc1-gallery-view.webp
├── 📄 products_wp_optimized.csv     ← استيراد WooCommerce
├── 📄 wp_alt_text_reference.csv     ← Alt Text للنسخ
├── 📄 wp_alt_text_reference.html    ← ← ← الأهم!
├── 📄 wp_seo_optimization_log.csv   ← سجل تفصيلي
└── 📄 wp_report.txt                 ← تقرير
```

---

## 🖼️ السيناريو 2: رفع الصور يدوياً لمكتبة الميديا + نسخ Alt Text

**هذا هو الجزء اليدوي — اتبع بالترتيب:**

### الخطوة 1: افتح ملف Alt Text المرجعي

افتح `wp_alt_text_reference.html` في المتصفح (Chrome / Firefox)

هتشوف جدول جميل هكذا:

```
┌──────────────────────────────────────────────────────────┐
│  📦 iPhone 15 Pro Max 512GB                              │
├──┬─────────────────────────────────────┬─────────────────┤
│# │ Image Filename                      │ Alt Text         │
├──┼─────────────────────────────────────┼─────────────────┤
│1 │ iphone-15-pro-max-abc1-main.webp    │ iPhone 15 Pro   │ ← اضغط لنسخه
│  │                                     │ Max - Electronics│
├──┼─────────────────────────────────────┼─────────────────┤
│2 │ iphone-15-pro-max-abc1-detail.webp  │ iPhone 15 Pro...│ ← اضغط لنسخه
└──┴─────────────────────────────────────┴─────────────────┘
```

> 💡 **اضغط على أي Alt Text في الجدول** → ينسخ تلقائياً للـ clipboard

### الخطوة 2: ارفع الصور لمكتبة الميديا

1. افتح WordPress → **Media** → **Add New**
2. ارفع صور المنتج الأول (WebP) من مجلد `wp_ready`
3. بعد رفع كل صورة:
   - اضغط عليها في مكتبة الميديا
   - في **"Alt Text"** الصق الـ Alt Text من الملف المرجعي
   - اضغط **Save**

### الخطوة 3: ربط الصور بالمنتجات (3 طرق)

**الطريقة أ — استيراد CSV (الأسهل):**
1. WooCommerce → **Products** → **Import**
2. اختر `products_wp_optimized.csv`
3. اضغط **"Run the importer"**
4. ✅ الصور هتتربط تلقائياً

**الطريقة ب — يدوياً لكل منتج:**
1. افتح المنتج في WordPress
2. في **"Product image"** اختر الصورة الرئيسية من مكتبة الميديا
3. في **"Product gallery"** أضف باقي الصور
4. اضغط **Update**

---

## 🎯 السيناريو 3: عندي صور فقط (بدون CSV WooCommerce)

**مناسب لو مش عندك CSV أو عايز تضغط صور بسرعة:**

1. شغّل الأداة → تبويب **🌐 WordPress**
2. اختر: `Direct Images / Archive (ZIP/RAR)`
3. اضغط **"Choose Images/ZIP"** واختر ملفاتك
4. اختر مجلد الحفظ
5. اضغط **START** ✅

---
---

# ⚙️ إعدادات متقدمة

## جودة الضغط (Quality)

| القيمة | النتيجة | متى تستخدمها |
|---|---|---|
| **95%** | جودة ممتازة، حجم أكبر | منتجات فاخرة، مجوهرات |
| **85%** ✅ | توازن مثالي (موصى به) | معظم المنتجات |
| **75%** | ضغط أقوى، جودة مقبولة | لو الحجم مهم جداً |
| **60%** | ضغط عالي، جودة منخفضة | صور thumbnail صغيرة |

## Workers (عمليات متوازية)
- **10** = الافتراضي، مناسب لمعظم الأجهزة ✅
- **5** = لو جهازك قديم أو الإنترنت بطيء
- **20** = لو عندك جهاز قوي وإنترنت سريع

---

# ❓ مشاكل شائعة وحلولها

| المشكلة | السبب | الحل |
|---|---|---|
| الأداة مش بتفتح | Python مش مثبت | راجع الخطوة 1 |
| خطأ عند التشغيل | المكتبات مش مثبتة | راجع الخطوة 2 |
| الصور مش بتتحمل | رابط شوبيفاي انتهى أو مكسور | جرب تحمّل من شوبيفاي مباشرة |
| ملف CSV مش بيتقرأ | ترميز الملف غير صحيح | احفظ الـ CSV بترميز UTF-8 |
| ZIP مش بيتفك | ملف RAR يحتاج WinRAR | ثبّت WinRAR أو استخدم ZIP |
| الصور الجديدة مش ظاهرة على شوبيفاي | Cache | امسح cache المتجر |

---

# 📁 ملخص المخرجات

## شوبيفاي
```
products_seo_optimized.csv     → استورده في شوبيفاي مباشرة
seo_optimization_log.csv       → سجل: الاسم القديم → الاسم الجديد
report.txt                     → إحصائيات وملخص
compressed_images/             → الصور المضغوطة WebP
```

## ووردبريس
```
products_wp_optimized.csv      → استورده في WooCommerce
wp_alt_text_reference.html     → افتحه في المتصفح وانسخ Alt Text
wp_alt_text_reference.csv      → نفس البيانات بصيغة جدول
wp_seo_optimization_log.csv    → سجل تفصيلي لكل صورة
wp_report.txt                  → إحصائيات وملخص
wp_compressed_images/          → الصور المضغوطة WebP
```

---

> 🛠️ **صُمِّمت هذه الأداة لتحسين ترتيب صور منتجاتك في نتائج Google 2026**
>
> للدعم الفني: راجع ملف `PROJECT_ARCHITECTURE.md` للمطورين
