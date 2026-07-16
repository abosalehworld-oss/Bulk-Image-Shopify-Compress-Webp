# 📖 دليل المستخدم الكامل — أداة تحسين صور المنتجات
## Bulk Image SEO Tool — Complete User Guide

> **للمبتدئين** — اتبع الخطوات بالترتيب ← ✅

---

## 🚀 تشغيل الأداة — خطوة واحدة فقط

### 🖱️ دوبل كليك على ملف `تشغيل_الأداة.bat`

**وخلاص — الملف يعمل كل شيء تلقائياً:**

```
✅ يفحص إذا كان Python مثبتاً
✅ لو مش مثبت → يفتح صفحة التحميل تلقائياً
✅ يثبّت المكتبات المطلوبة تلقائياً (مرة واحدة فقط)
✅ يشغّل الأداة
```

---

### ❓ لو فتح صفحة تحميل Python (مرة واحدة فقط)

هذا يحدث فقط في **أول مرة** إذا لم يكن Python مثبتاً:

1. حمّل Python من الصفحة التي فتحت
2. شغّل ملف التثبيت
3. ✅ **مهم:** ضع علامة على **"Add Python to PATH"**
4. اضغط **Install Now**
5. بعد الانتهاء — **دوبل كليك على `تشغيل_الأداة.bat` مرة ثانية**

> 💡 بعد هذه المرة لن تحتاج لأي شيء — الأداة ستفتح مباشرة في كل مرة

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
- **Download Folder:** اضغط "Choose" واختر مجلد لحفظ الصور المحملة
- **Compress Folder:** اضغط "Choose" واختر مجلد للصور المضغوطة

**④ الإعدادات (اتركها كما هي للمبتدئين)**
- Quality: **85%** ✅
- Workers: **10** ✅

**⑤ اضغط START وانتظر DONE ✅**

**⑥ النتائج**
```
📁 compressed_images/
├── 📁 product-handle-1/
│   ├── brand-product-perfume-decant.webp
│   ├── brand-product-fragrance-detail.webp
│   └── ...
├── 📄 products_seo_optimized.csv    ← للاستيراد في شوبيفاي
├── 📄 seo_optimization_log.csv      ← سجل التحسينات
└── 📄 report.txt                    ← تقرير
```

---

## 🗜️ السيناريو 2: عندي صور على جهازي (بدون CSV شوبيفاي)

**الهدف:** ضغط صور موجودة + تسمية SEO

### الخطوات:

**① رتّب صورك في مجلدات**
```
📁 my_products/
├── 📁 tom-ford-tobacco-vanille/
│   ├── photo1.jpg
│   └── photo2.jpg
├── 📁 xerjoff-naxos/
│   └── img1.png
```
> 💡 اسم المجلد هو اللي بيبني اسم الملف SEO منه

**② شغّل الأداة**
1. تبويب **🛒 Shopify** → **"Choose Mode"**: `🗜️ Compress Only`
2. **"Input Source"**: `Direct Images / Archive (ZIP/RAR)`
3. اضغط **"Choose Images/ZIP"** واختر الملفات
4. اضغط **START** ✅

---

## 📤 السيناريو 3: رفع الصور المحسّنة على شوبيفاي

### طريقة 1: استيراد CSV (الأسهل)
1. شوبيفاي → **Products** → **Import**
2. اختر `products_seo_optimized.csv`
3. ✅ شوبيفاي يحدّث كل المنتجات تلقائياً

### طريقة 2: رفع يدوي
1. افتح كل منتج على شوبيفاي
2. احذف الصور القديمة
3. ارفع صور WebP الجديدة من مجلد `compressed_images`

---
---

# 🌐 قسم ثاني: ووردبريس / WooCommerce

> ⚠️ **وضع ووردبريس: كل شيء على جهازك — لا رفع تلقائي**
> الرفع يدوي لمكتبة الميديا للأمان الكامل

---

## 📦 السيناريو 1: عندي ملف CSV من WooCommerce

### الخطوة 1: تصدير CSV من WooCommerce
1. لوحة التحكم WordPress → **WooCommerce** → **Products** → **Export**
2. اضغط **"Generate the CSV"**
3. احفظ الملف على جهازك

### الخطوة 2: رتّب صورك في مجلدات
```
📁 product_images/
├── 📁 iphone-15-pro-max/
│   ├── front.jpg
│   └── back.jpg
├── 📁 samsung-galaxy-s24/
│   └── main.jpg
```

### الخطوة 3: شغّل الأداة
1. تبويب **🌐 WordPress**
2. **"Input Source"**: `WooCommerce CSV`
3. اختر ملف CSV ومجلد الصور ومجلد الحفظ
4. اضغط **START** وانتظر **Done! ✅**

### الخطوة 4: النتائج
```
📁 wp_ready/
├── 📁 iphone-15-pro-max/
│   ├── iphone-15-pro-max-abc1-main-product-image.webp
│   ├── iphone-15-pro-max-abc1-detail-view.webp
│   └── iphone-15-pro-max-abc1-gallery-view.webp
├── 📄 products_wp_optimized.csv       ← استيراد WooCommerce
├── 📄 wp_alt_text_reference.html      ← ← ← الأهم! افتحه في المتصفح
├── 📄 wp_alt_text_reference.csv       ← Alt Text جدول
├── 📄 wp_seo_optimization_log.csv     ← سجل تفصيلي
└── 📄 wp_report.txt                   ← تقرير
```

---

## 🖼️ السيناريو 2: رفع الصور يدوياً لمكتبة الميديا

### الخطوة 1: افتح ملف Alt Text المرجعي
افتح `wp_alt_text_reference.html` في المتصفح (Chrome / Firefox)

```
┌──────────────────────────────────────────────────┐
│  📦 iPhone 15 Pro Max 512GB                      │
├──┬──────────────────────────────┬────────────────┤
│ # │ Image Filename              │ Alt Text        │
├──┼──────────────────────────────┼────────────────┤
│ 1 │ iphone-...main.webp         │ iPhone 15 Pro.. │ ← اضغط لنسخه
│ 2 │ iphone-...detail.webp       │ iPhone 15 Pro.. │ ← اضغط لنسخه
└──┴──────────────────────────────┴────────────────┘
```
> 💡 **اضغط على أي Alt Text** → ينسخ تلقائياً

### الخطوة 2: ارفع الصور لمكتبة الميديا
1. WordPress → **Media** → **Add New**
2. ارفع الصور WebP
3. لكل صورة: افتحها → **"Alt Text"** → الصق → **Save**

### الخطوة 3: ربط الصور بالمنتجات

**الطريقة أ — استيراد CSV:**
- WooCommerce → **Products** → **Import** → اختر `products_wp_optimized.csv`

**الطريقة ب — يدوياً:**
- افتح المنتج → **Product image** / **Product gallery** → اختر من مكتبة الميديا

---

## 🎯 السيناريو 3: عندي صور فقط (بدون CSV)
1. تبويب **🌐 WordPress** → `Direct Images / Archive (ZIP/RAR)`
2. اختر ملفاتك → اضغط **START** ✅

---
---

# ⚙️ إعدادات متقدمة

## جودة الضغط (Quality)

| القيمة | النتيجة | متى تستخدمها |
|---|---|---|
| **95%** | جودة ممتازة، حجم أكبر | منتجات فاخرة، مجوهرات |
| **85%** ✅ | توازن مثالي **(موصى به)** | معظم المنتجات |
| **75%** | ضغط أقوى | لو الحجم مهم جداً |
| **60%** | ضغط عالي | صور thumbnail صغيرة |

## Workers (عمليات متوازية)
- **10** ✅ = الافتراضي، مناسب لمعظم الأجهزة
- **5** = لو جهازك قديم أو الإنترنت بطيء
- **20** = لو عندك جهاز قوي وإنترنت سريع

---

# ❓ مشاكل شائعة وحلولها

| المشكلة | الحل |
|---|---|
| الأداة مش بتفتح | دوبل كليك على `تشغيل_الأداة.bat` مرة أخرى |
| طلب تحميل Python | حمّله، ✅ اختر "Add to PATH"، ثم شغّل الملف مجدداً |
| فشل تثبيت المكتبات | كليك يمين على الملف → **Run as Administrator** |
| ملف CSV مش بيتقرأ | احفظ الـ CSV بترميز **UTF-8** من Excel |
| ZIP مش بيتفك | استخدم ZIP بدل RAR، أو ثبّت WinRAR |
| الصور مش ظاهرة على شوبيفاي | امسح الـ cache من إعدادات المتجر |

---

# 📁 ملخص المخرجات

## شوبيفاي
| الملف | الوظيفة |
|---|---|
| `products_seo_optimized.csv` | استورده في شوبيفاي مباشرة |
| `seo_optimization_log.csv` | سجل: الاسم القديم ← الاسم الجديد + Alt Text |
| `report.txt` | إحصائيات وملخص |
| `compressed_images/` | الصور المضغوطة WebP |

## ووردبريس
| الملف | الوظيفة |
|---|---|
| `products_wp_optimized.csv` | استورده في WooCommerce |
| `wp_alt_text_reference.html` | **افتحه في المتصفح** — انسخ Alt Text بنقرة |
| `wp_alt_text_reference.csv` | نفس البيانات بصيغة جدول |
| `wp_seo_optimization_log.csv` | سجل تفصيلي لكل صورة |
| `wp_report.txt` | إحصائيات وملخص |
| `wp_compressed_images/` | الصور المضغوطة WebP |

---

> 🛠️ **صُمِّمت هذه الأداة لتحسين ترتيب صور منتجاتك في نتائج Google 2026**
>
> للمطورين: راجع `PROJECT_ARCHITECTURE.md`
