#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهة رسومية لأداة تحميل وضغط صور المنتجات
Bulk Image Tool - GUI (Shopify + WordPress)

يدعم:
  • Shopify: تحميل + ضغط + تسمية SEO + رفع
  • WordPress/WooCommerce: ضغط + تسمية SEO + Alt Text (بدون API)

تشغيل: py shopify_gui.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import time
import queue
import re
import zipfile
import shutil
try:
    import rarfile
    RAR_AVAILABLE = True
except ImportError:
    RAR_AVAILABLE = False

from shopify_image_downloader import (
    ShopifyCSVParser, ImageDownloader, ImageCompressor,
    ReportGenerator, ImageDownloader as Formatter,
    ShopifyCSVExporter, SEO_AVAILABLE
)

if SEO_AVAILABLE:
    from seo_helpers import SEOLogger

# ── WordPress modules ──
try:
    from wordpress_image_processor import (
        WooCommerceCSVParser, WordPressImageCompressor,
        WooCommerceCSVExporter, WordPressAltTextExporter,
        WordPressReportGenerator
    )
    from wordpress_seo_helpers import WPSEOLogger
    WP_AVAILABLE = True
except ImportError:
    WP_AVAILABLE = False


class ShopifyImageGUI:
    """واجهة رسومية بسيطة لأداة صور شوبيفاي - تحميل وضغط فقط."""

    BG_DARK = "#1a1a2e"
    BG_CARD = "#16213e"
    BG_INPUT = "#0f3460"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#ff6b81"
    GREEN = "#2ecc71"
    YELLOW = "#f1c40f"
    TEXT = "#ecf0f1"
    TEXT_DIM = "#95a5a6"
    CYAN = "#00d2d3"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bulk Image Tool — Shopify & WordPress")
        self.root.geometry("900x780")
        self.root.minsize(800, 700)
        self.root.configure(bg=self.BG_DARK)

        # متغيرات
        self.input_source = tk.StringVar(value="csv")
        self.local_files = []
        self.csv_path = tk.StringVar()
        self.download_folder = tk.StringVar()
        self.compress_folder = tk.StringVar()
        self.quality = tk.IntVar(value=85)
        self.workers = tk.IntVar(value=10)
        self.mode = tk.StringVar(value="download_compress")

        # حالة التشغيل
        self.is_running = False
        self.should_stop = False
        self.log_queue = queue.Queue()

        self._build_ui()
        self.root.after(100, self._poll_log)

    def _build_ui(self):
        # ─── Header ───
        hdr = tk.Frame(self.root, bg=self.ACCENT, height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Bulk Image SEO Tool   -   أداة صور المنتجات بالجملة",
                 font=("Segoe UI", 14, "bold"), fg="white", bg=self.ACCENT).pack(pady=10)

        # ─── Platform Tabs (Shopify | WordPress) ───
        self.active_platform = tk.StringVar(value="shopify")
        tab_bar = tk.Frame(self.root, bg="#0d1b2a", height=42)
        tab_bar.pack(fill=tk.X)
        tab_bar.pack_propagate(False)

        self._tab_btns = {}
        for val, label, icon in [
            ("shopify", "Shopify", "🛒"),
            ("wordpress", "WordPress", "🌐"),
        ]:
            btn = tk.Button(
                tab_bar, text=f"  {icon}  {label}  ",
                font=("Segoe UI", 12, "bold"),
                fg="white", relief=tk.FLAT, padx=20, pady=6,
                cursor="hand2",
                command=lambda v=val: self._switch_platform(v),
            )
            btn.pack(side=tk.LEFT, padx=2, pady=4)
            self._tab_btns[val] = btn

        if not WP_AVAILABLE:
            self._tab_btns["wordpress"].config(state=tk.DISABLED, fg="#666")

        # ─── Platform Frames Container ───
        self._platform_container = tk.Frame(self.root, bg=self.BG_DARK)
        self._platform_container.pack(fill=tk.BOTH, expand=True)

        # === Shopify Frame (original UI) ===
        self._shopify_frame = tk.Frame(self._platform_container, bg=self.BG_DARK)
        self._wp_frame = tk.Frame(self._platform_container, bg=self.BG_DARK)

        self._build_shopify_tab(self._shopify_frame)
        if WP_AVAILABLE:
            self._build_wp_tab(self._wp_frame)

        # عرض Shopify كافتراضي
        self._switch_platform("shopify")

    def _switch_platform(self, platform):
        """تبديل بين تبويبات Shopify و WordPress."""
        self.active_platform.set(platform)
        # إخفاء الكل
        self._shopify_frame.pack_forget()
        self._wp_frame.pack_forget()
        # تحديث ألوان التبويبات
        for val, btn in self._tab_btns.items():
            if val == platform:
                btn.config(bg=self.ACCENT, activebackground=self.ACCENT_HOVER)
            else:
                btn.config(bg="#1a2744", activebackground="#253a5e")
        # عرض التبويب المختار
        if platform == "shopify":
            self._shopify_frame.pack(fill=tk.BOTH, expand=True)
        elif platform == "wordpress":
            self._wp_frame.pack(fill=tk.BOTH, expand=True)

    def _build_shopify_tab(self, parent):
        """بناء واجهة Shopify (نفس الواجهة الأصلية بالكامل)."""

        # ─── Scrollable ───
        canvas = tk.Canvas(parent, bg=self.BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        self.content = tk.Frame(canvas, bg=self.BG_DARK)
        self.content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.content, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # ═══ 1. اختيار الوضع ═══
        c1 = self._card("Choose Mode   -   اختر الوضع")
        modes = [
            ("download_compress", "Download + Compress   تحميل + ضغط",
             "تحميل الصور من شوبيفاي ثم ضغطها تلقائياً"),
            ("download_only", "Download Only   تحميل فقط",
             "تحميل بس - تضغط بنفسك ببرنامج تاني"),
            ("compress_only", "Compress Only   ضغط فقط",
             "ضغط صور موجودة على جهازك"),
        ]
        for val, label, desc in modes:
            row = tk.Frame(c1, bg=self.BG_CARD)
            row.pack(fill=tk.X, pady=2)
            tk.Radiobutton(row, text=label, variable=self.mode, value=val,
                           font=("Segoe UI", 11, "bold"), fg=self.TEXT, bg=self.BG_CARD,
                           selectcolor=self.BG_INPUT, activebackground=self.BG_CARD,
                           activeforeground=self.CYAN, anchor="e",
                           command=self._on_mode_change).pack(side=tk.RIGHT)
            tk.Label(row, text=desc, font=("Segoe UI", 9), fg=self.TEXT_DIM,
                     bg=self.BG_CARD).pack(side=tk.RIGHT, padx=(0, 15))

        # ═══ 2. مصدر الإدخال وملفات الإدخال ═══
        self.input_card = self._card("Input Source & Files   -   مصدر وملفات الإدخال")
        
        # اختيار المصدر
        src_row = tk.Frame(self.input_card, bg=self.BG_CARD)
        src_row.pack(fill=tk.X, pady=(0, 5))
        tk.Radiobutton(src_row, text="Shopify CSV", variable=self.input_source, value="csv",
                       font=("Segoe UI", 10, "bold"), fg=self.TEXT, bg=self.BG_CARD,
                       selectcolor=self.BG_INPUT, activebackground=self.BG_CARD,
                       activeforeground=self.CYAN, anchor="w",
                       command=self._on_source_change).pack(side=tk.LEFT)
        tk.Radiobutton(src_row, text="Direct Images / Archive (ZIP/RAR)", variable=self.input_source, value="local",
                       font=("Segoe UI", 10, "bold"), fg=self.TEXT, bg=self.BG_CARD,
                       selectcolor=self.BG_INPUT, activebackground=self.BG_CARD,
                       activeforeground=self.CYAN, anchor="w",
                       command=self._on_source_change).pack(side=tk.LEFT, padx=15)
                       
        tk.Frame(self.input_card, bg=self.BG_INPUT, height=1).pack(fill=tk.X, pady=5)

        # صف الـ CSV
        self.csv_row = tk.Frame(self.input_card, bg=self.BG_CARD)
        self.csv_row.pack(fill=tk.X, pady=2)
        self._file_row(self.csv_row, self.csv_path, "Choose CSV File   اختر ملف", self._browse_csv)

        # صف الصور المباشرة
        self.local_row = tk.Frame(self.input_card, bg=self.BG_CARD)
        self.local_lbl = tk.Label(self.local_row, text="No files selected   لم يتم اختيار ملفات", font=("Segoe UI", 10), fg=self.TEXT_DIM, bg=self.BG_CARD, anchor="w")
        self.local_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(self.local_row, text="📂 Choose Images/ZIP   اختر الصور/ZIP", font=("Segoe UI", 9, "bold"),
                  bg=self.ACCENT, fg="white", relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=self._browse_local,
                  activebackground=self.ACCENT_HOVER).pack(side=tk.RIGHT)

        # ═══ 3. مجلدات الحفظ ═══
        self.folders_card = self._card("Save Location   -   مكان الحفظ على جهازك")

        self.dl_frame = tk.Frame(self.folders_card, bg=self.BG_CARD)
        self.dl_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.dl_frame, text="Download Folder   مجلد التحميل:",
                 font=("Segoe UI", 10), fg=self.CYAN, bg=self.BG_CARD, anchor="e").pack(fill=tk.X)
        self._file_row(self.dl_frame, self.download_folder, "Choose Folder   اختر مجلد",
                       self._browse_dl, is_folder=True)

        self.comp_frame = tk.Frame(self.folders_card, bg=self.BG_CARD)
        self.comp_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.comp_frame, text="Compressed Folder   مجلد الصور المضغوطة:",
                 font=("Segoe UI", 10), fg=self.CYAN, bg=self.BG_CARD, anchor="e").pack(fill=tk.X)
        self._file_row(self.comp_frame, self.compress_folder, "Choose Folder   اختر مجلد",
                       self._browse_comp, is_folder=True)

        # ═══ 4. إعدادات ═══
        c4 = self._card("Settings   -   الإعدادات")
        srow = tk.Frame(c4, bg=self.BG_CARD)
        srow.pack(fill=tk.X, pady=4)

        # جودة الضغط
        tk.Label(srow, text="Compression Quality   جودة الضغط:", font=("Segoe UI", 10),
                 fg=self.TEXT, bg=self.BG_CARD).pack(side=tk.RIGHT, padx=(10, 0))
        self.qlbl = tk.Label(srow, text="85%", font=("Segoe UI", 10, "bold"),
                             fg=self.GREEN, bg=self.BG_CARD, width=4)
        self.qlbl.pack(side=tk.RIGHT, padx=5)
        tk.Scale(srow, from_=100, to=30, orient=tk.HORIZONTAL, variable=self.quality,
                 showvalue=False, bg=self.BG_CARD, fg=self.TEXT, troughcolor=self.BG_INPUT,
                 highlightthickness=0, length=150, sliderrelief=tk.FLAT,
                 command=lambda v: self.qlbl.config(text=f"{v}%")).pack(side=tk.RIGHT)

        # خيوط
        tk.Label(srow, text="  |  Threads   خيوط:", font=("Segoe UI", 10),
                 fg=self.TEXT, bg=self.BG_CARD).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Spinbox(srow, from_=1, to=50, textvariable=self.workers, width=4,
                   font=("Consolas", 11), bg=self.BG_INPUT, fg=self.TEXT,
                   buttonbackground=self.BG_INPUT, relief=tk.FLAT, borderwidth=5,
                   justify=tk.CENTER).pack(side=tk.RIGHT, padx=5)

        # ═══ أزرار ═══
        btns = tk.Frame(self.content, bg=self.BG_DARK)
        btns.pack(fill=tk.X, pady=10, padx=5)

        self.start_btn = tk.Button(btns, text="START   تشغيل   🚀",
                                   font=("Segoe UI", 14, "bold"),
                                   bg=self.GREEN, fg="white", relief=tk.FLAT,
                                   padx=30, pady=10, cursor="hand2",
                                   command=self._start, activebackground="#27ae60")
        self.start_btn.pack(side=tk.RIGHT, padx=8)

        self.stop_btn = tk.Button(btns, text="STOP   إيقاف   ⏹",
                                  font=("Segoe UI", 14, "bold"),
                                  bg="#e74c3c", fg="white", relief=tk.FLAT,
                                  padx=30, pady=10, cursor="hand2",
                                  command=self._stop, activebackground="#c0392b",
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=8)

        tk.Button(btns, text="Open Folder   فتح المجلد   📁",
                  font=("Segoe UI", 11), bg=self.BG_INPUT, fg=self.TEXT,
                  relief=tk.FLAT, padx=15, pady=10, cursor="hand2",
                  command=self._open_folder, activebackground=self.BG_CARD
                  ).pack(side=tk.LEFT, padx=8)

        # ═══ شريط التقدم ═══
        pf = tk.Frame(self.content, bg=self.BG_DARK)
        pf.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.status_lbl = tk.Label(pf, text="Ready   جاهز للتشغيل...",
                                   font=("Segoe UI", 10), fg=self.TEXT_DIM,
                                   bg=self.BG_DARK, anchor="e")
        self.status_lbl.pack(fill=tk.X)

        style = ttk.Style()
        style.theme_use('default')
        style.configure("G.Horizontal.TProgressbar",
                        troughcolor=self.BG_INPUT, background=self.GREEN, thickness=18)
        self.pbar = ttk.Progressbar(pf, style="G.Horizontal.TProgressbar",
                                     mode='determinate', maximum=100)
        self.pbar.pack(fill=tk.X, pady=4)

        self.detail_lbl = tk.Label(pf, text="", font=("Consolas", 9),
                                   fg=self.TEXT_DIM, bg=self.BG_DARK, anchor="e")
        self.detail_lbl.pack(fill=tk.X)

        # ═══ سجل ═══
        lc = self._card("Log   السجل")
        self.log = scrolledtext.ScrolledText(lc, height=10, font=("Consolas", 10),
                                              bg="#0a0a1a", fg=self.GREEN,
                                              insertbackground=self.GREEN,
                                              relief=tk.FLAT, borderwidth=8,
                                              wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.tag_config("error", foreground="#e74c3c")
        self.log.tag_config("warning", foreground="#f39c12")
        self.log.tag_config("success", foreground="#2ecc71")
        self.log.tag_config("info", foreground="#3498db")
        self.log.tag_config("header", foreground="#00d2d3", font=("Consolas", 10, "bold"))

        self._on_mode_change()

    # ─── أدوات بناء ───
    def _card(self, title):
        c = tk.Frame(self.content, bg=self.BG_CARD, padx=15, pady=10,
                     highlightbackground=self.BG_INPUT, highlightthickness=1)
        c.pack(fill=tk.X, pady=5, padx=5)
        tk.Label(c, text=title, font=("Segoe UI", 12, "bold"),
                 fg=self.CYAN, bg=self.BG_CARD, anchor="e").pack(fill=tk.X)
        tk.Frame(c, bg=self.CYAN, height=1).pack(fill=tk.X, pady=(3, 6))
        return c

    def _file_row(self, parent, var, btn_text, cmd, is_folder=False):
        r = tk.Frame(parent, bg=self.BG_CARD)
        r.pack(fill=tk.X, pady=2)
        tk.Entry(r, textvariable=var, font=("Consolas", 10), bg=self.BG_INPUT,
                 fg=self.TEXT, insertbackground=self.TEXT, relief=tk.FLAT,
                 borderwidth=6).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(r, text=f"📂 {btn_text}", font=("Segoe UI", 9, "bold"),
                  bg=self.ACCENT, fg="white", relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=cmd,
                  activebackground=self.ACCENT_HOVER).pack(side=tk.RIGHT)

    # ─── أحداث ───
    def _on_source_change(self):
        src = self.input_source.get()
        if src == "csv":
            self.csv_row.pack(fill=tk.X, pady=2)
            self.local_row.pack_forget()
            self._on_mode_change()
        else:
            self.local_row.pack(fill=tk.X, pady=2)
            self.csv_row.pack_forget()
            self.dl_frame.pack_forget()
            self.comp_frame.pack(fill=tk.X, pady=3)

    def _on_mode_change(self):
        if self.input_source.get() == "local":
            self.dl_frame.pack_forget()
            self.comp_frame.pack(fill=tk.X, pady=3)
            return

        m = self.mode.get()
        self.dl_frame.pack_forget()
        self.comp_frame.pack_forget()
        if m == "download_compress":
            self.dl_frame.pack(fill=tk.X, pady=3)
            self.comp_frame.pack(fill=tk.X, pady=3)
        elif m == "download_only":
            self.dl_frame.pack(fill=tk.X, pady=3)
        elif m == "compress_only":
            self.dl_frame.pack(fill=tk.X, pady=3)
            self.comp_frame.pack(fill=tk.X, pady=3)

    def _browse_local(self):
        files = filedialog.askopenfilenames(title="Choose Images or ZIP/RAR Archive",
                                            filetypes=[("Images & Archives", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.zip *.rar"), ("All", "*.*")])
        if files:
            self.local_files = list(files)
            if len(self.local_files) == 1:
                name = os.path.basename(self.local_files[0])
                self.local_lbl.config(text=f"Selected: {name}")
            else:
                self.local_lbl.config(text=f"Selected {len(self.local_files)} files")
            
            base = os.path.dirname(self.local_files[0])
            if not self.compress_folder.get():
                self.compress_folder.set(os.path.join(base, "compressed_images"))

    def _browse_csv(self):
        p = filedialog.askopenfilename(title="Choose CSV File",
                                        filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if p:
            self.csv_path.set(p)
            base = os.path.dirname(p)
            if not self.download_folder.get():
                self.download_folder.set(os.path.join(base, "downloaded_images"))
            if not self.compress_folder.get():
                self.compress_folder.set(os.path.join(base, "compressed_images"))

    def _browse_dl(self):
        p = filedialog.askdirectory(title="Choose Download Folder")
        if p: self.download_folder.set(p)

    def _browse_comp(self):
        p = filedialog.askdirectory(title="Choose Compressed Folder")
        if p: self.compress_folder.set(p)

    def _open_folder(self):
        for p in [self.compress_folder.get(), self.download_folder.get()]:
            if p and os.path.exists(p):
                os.startfile(p)
                return
        if self.csv_path.get():
            os.startfile(os.path.dirname(self.csv_path.get()))

    # ─── تشغيل / إيقاف ───
    def _start(self):
        if self.input_source.get() == "csv":
            if not self.csv_path.get() or not os.path.exists(self.csv_path.get()):
                messagebox.showwarning("Warning", "Choose a valid CSV file first!\nاختر ملف CSV صحيح!")
                return
            if not self.download_folder.get():
                messagebox.showwarning("Warning", "Choose download folder!\nاختر مجلد التحميل!")
                return
            if self.mode.get() in ("download_compress", "compress_only") and not self.compress_folder.get():
                messagebox.showwarning("Warning", "Choose compressed folder!\nاختر مجلد الضغط!")
                return
        else:
            if not self.local_files:
                messagebox.showwarning("Warning", "Choose images or archive first!\nاختر الصور أو الملف المضغوط!")
                return
            if not self.compress_folder.get():
                messagebox.showwarning("Warning", "Choose compressed folder!\nاختر مجلد الضغط!")
                return

        self.is_running = True
        self.should_stop = False
        self.start_btn.config(state=tk.DISABLED, bg="#7f8c8d")
        self.stop_btn.config(state=tk.NORMAL)
        self.pbar['value'] = 0
        self.log.config(state=tk.NORMAL)
        self.log.delete(1.0, tk.END)
        self.log.config(state=tk.DISABLED)

        threading.Thread(target=self._run, daemon=True).start()

    def _stop(self):
        if self.is_running:
            self.should_stop = True
            self._logmsg("STOPPED - will finish current image then stop", "warning")
            self._logmsg("تم الإيقاف - هيكمل الصورة الحالية ويقف", "warning")

    def _finish(self, ok=True):
        self.is_running = False
        self.should_stop = False
        self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL, bg=self.GREEN))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
        if ok:
            self.root.after(0, lambda: self.status_lbl.config(text="Done!   اكتملت العملية بنجاح! 🎉", fg=self.GREEN))
            self.root.after(0, lambda: self.pbar.configure(value=100))
        else:
            self.root.after(0, lambda: self.status_lbl.config(text="Stopped   تم الإيقاف 🛑", fg=self.YELLOW))

    # ─── العملية الرئيسية ───
    def _run(self):
        try:
            mode = self.mode.get()
            dl_dir = self.download_folder.get()
            comp_dir = self.compress_folder.get()
            t0 = time.time()

            # 1. قراءة الإدخال
            products = {}
            temp_extract_dir = ""
            
            if self.input_source.get() == "csv":
                self._logmsg("=" * 50, "header")
                self._logmsg("Reading CSV...   قراءة ملف CSV...", "header")
                self._set_status("Reading CSV...   قراءة ملف CSV...")
                self._set_pbar(5)

                parser = ShopifyCSVParser(self.csv_path.get())
                products = parser.parse()
                if not products:
                    self._logmsg("ERROR: No products found!   لم يتم العثور على منتجات!", "error")
                    self._finish(False)
                    return

                total_imgs = sum(len(p['images']) for p in products.values())
                self._logmsg(f"Found {len(products)} products, {total_imgs} images", "success")
                self._logmsg(f"تم العثور على {len(products)} منتج و {total_imgs} صورة", "success")
                self._set_pbar(10)
            else:
                self._logmsg("=" * 50, "header")
                self._logmsg("Preparing Local Files/Archive...   تحضير الملفات المباشرة...", "header")
                self._set_status("Preparing files...   تحضير الملفات...")
                self._set_pbar(5)
                
                # إعداد مجلد مؤقت
                temp_extract_dir = os.path.join(comp_dir, "temp_extracted_images_to_compress")
                os.makedirs(temp_extract_dir, exist_ok=True)
                dl_dir = temp_extract_dir # to fool the rest of the script that this is the downloaded dir
                
                total_imgs = 0
                
                # نقل واستخراج الملفات
                for fpath in self.local_files:
                    ext = fpath.lower().split('.')[-1]
                    if ext in ['zip']:
                        self._logmsg(f"Extracting ZIP: {os.path.basename(fpath)}", "info")
                        try:
                            with zipfile.ZipFile(fpath, 'r') as z:
                                z.extractall(temp_extract_dir)
                        except Exception as e:
                            self._logmsg(f"Error extracting ZIP: {e}", "error")
                    elif ext in ['rar']:
                        self._logmsg(f"Extracting RAR: {os.path.basename(fpath)}", "info")
                        if RAR_AVAILABLE:
                            try:
                                with rarfile.RarFile(fpath) as r:
                                    r.extractall(temp_extract_dir)
                            except Exception as e:
                                self._logmsg(f"Error extracting RAR: {e}", "error")
                        else:
                            self._logmsg("RAR support not installed. Please pip install rarfile and have UnRAR in PATH.", "error")
                    elif ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'avif']:
                        # Create a folder for the image to act as the handle
                        base_name = os.path.splitext(os.path.basename(fpath))[0]
                        safe_handle = re.sub(r'[<>:"/\\|?*]', '_', base_name).strip('. ') or 'unknown'
                        target_dir = os.path.join(temp_extract_dir, safe_handle)
                        os.makedirs(target_dir, exist_ok=True)
                        shutil.copy2(fpath, os.path.join(target_dir, os.path.basename(fpath)))
                        
                # Now scan temp_extract_dir to build products
                for root, dirs, files in os.walk(temp_extract_dir):
                    rel_dir = os.path.relpath(root, temp_extract_dir)
                    # Use the first-level folder name as handle, or if it's in root, use 'direct_images'
                    if rel_dir == '.':
                        continue
                    
                    # Ensure we have images
                    imgs = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'))]
                    if not imgs:
                        continue
                        
                    parts = rel_dir.replace('\\', '/').split('/')
                    handle = parts[0]
                    
                    if handle not in products:
                        products[handle] = {
                            'title': handle,
                            'vendor': '',
                            'body_html': '',
                            'type': '',
                            'tags': '',
                            'olfactory_family': '',
                            'scent': '',
                            'season': '',
                            'target_gender': '',
                            'fragrance': '',
                            'sizes': [],
                            'images': []
                        }
                    total_imgs += len(imgs)
                    
                if not products:
                    self._logmsg("ERROR: No valid images found in input!   لم يتم العثور على صور صحيحة!", "error")
                    self._finish(False)
                    return
                    
                self._logmsg(f"Found {len(products)} handles/folders, {total_imgs} images", "success")
                self._set_pbar(10)

            if self.should_stop:
                self._finish(False)
                return

            download_stats = {}
            compress_stats = {}

            # 2. تحميل
            if mode in ("download_compress", "download_only") and self.input_source.get() == "csv":
                self._logmsg("\n" + "=" * 50, "header")
                self._logmsg("Downloading images...   جاري تحميل الصور...", "header")
                self._logmsg(f"Saving to: {dl_dir}", "info")
                self._set_status("Downloading...   جاري التحميل...")

                downloader = ImageDownloader(output_dir=dl_dir, workers=self.workers.get())
                tasks = []
                for handle, prod in products.items():
                    pdir = os.path.join(dl_dir, downloader._sanitize_dirname(handle))
                    title = prod.get('title', '') or handle
                    safe_title = downloader._sanitize_filename(title)
                    total_imgs = len(prod['images'])
                    for idx, img_data in enumerate(prod['images'], 1):
                        if isinstance(img_data, dict):
                            url = img_data['url']
                            position = img_data.get('position', idx)
                        else:
                            url = img_data
                            position = idx
                        ext = downloader._get_extension(url)
                        if total_imgs == 1:
                            fname = f"{safe_title}{ext}"
                        else:
                            fname = f"{safe_title}-{position}{ext}"
                        tasks.append((url, os.path.join(pdir, fname), handle))

                done = 0
                total = len(tasks)
                from concurrent.futures import ThreadPoolExecutor, as_completed

                with ThreadPoolExecutor(max_workers=self.workers.get()) as ex:
                    futs = {ex.submit(downloader._download_single, u, p, h): h for u, p, h in tasks}
                    for f in as_completed(futs):
                        if self.should_stop:
                            ex.shutdown(wait=False, cancel_futures=True)
                            self._finish(False)
                            return
                        r = f.result()
                        done += 1
                        if r['status'] == 'success':
                            downloader.stats['success'] += 1
                            downloader.stats['total_size'] += r['size']
                            self._logmsg(f"  OK  {r['handle']}/{os.path.basename(r['path'])}", "success")
                        elif r['status'] == 'skipped':
                            downloader.stats['skipped'] += 1
                            downloader.stats['total_size'] += r['size']
                        else:
                            downloader.stats['failed'] += 1
                            self._logmsg(f"  FAIL  {r['handle']}: {r.get('error','')[:60]}", "error")
                        self._set_pbar(10 + int((done / max(total, 1)) * 40))
                        self._set_detail(f"Downloaded {done}/{total}")

                download_stats = downloader.stats
                sz = Formatter._format_size(download_stats['total_size'])
                self._logmsg(f"\nDownload done: {download_stats['success']} OK | "
                             f"{download_stats['skipped']} skipped | "
                             f"{download_stats['failed']} failed | {sz}", "success")

            # 3. ضغط
            if mode in ("download_compress", "compress_only"):
                if self.should_stop:
                    self._finish(False)
                    return

                src = dl_dir
                self._logmsg("\n" + "=" * 50, "header")
                self._logmsg(f"SEO Compressing (quality: {self.quality.get()}%)...   ضغط + تحسين SEO...", "header")
                self._set_status("SEO Compressing...   جاري الضغط + SEO...")

                compressor = ImageCompressor(input_dir=src, output_dir=comp_dir,
                                             quality=self.quality.get())

                if SEO_AVAILABLE:
                    # ضغط مع SEO
                    if self.input_source.get() == "csv":
                        csv_dir = os.path.dirname(self.csv_path.get())
                    else:
                        csv_dir = comp_dir
                        
                    seo_log_path = os.path.join(csv_dir, 'seo_optimization_log.csv')
                    seo_logger_inst = SEOLogger(log_path=seo_log_path)

                    # عد الصور للتقدم
                    img_count = 0
                    for handle in products:
                        handle_dir = os.path.join(src, re.sub(r'[<>:"/\\|?*]', '_', handle).strip('. ') or 'unknown_product')
                        if os.path.exists(handle_dir):
                            img_count += sum(1 for f in os.listdir(handle_dir)
                                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif')))

                    self._logmsg(f"  Found {img_count} images to process", "info")

                    def update_progress(done, total):
                        if self.should_stop: return False
                        self._set_pbar(50 + int((done / max(total, 1)) * 50))
                        self._set_detail(f"SEO Compressing {done}/{total}")
                        self.root.update_idletasks()
                        return True

                    compress_stats_result = compressor.compress_all_seo(products, seo_logger_inst, progress_callback=update_progress)

                    # حفظ SEO log
                    seo_logger_inst.save()
                    self._logmsg(f"  SEO Log saved: {seo_log_path}", "success")
                    self._logmsg(f"  {seo_logger_inst.get_summary()}", "info")

                    # تصدير CSV محسّن
                    if self.input_source.get() == "csv":
                        seo_csv_path = os.path.join(csv_dir, 'products_seo_optimized.csv')
                        exporter = ShopifyCSVExporter(
                            original_csv=self.csv_path.get(),
                            seo_map=compressor.seo_map,
                            output_path=seo_csv_path
                        )
                        exporter.export()
                        self._logmsg(f"  SEO CSV saved: {seo_csv_path}", "success")
                    else:
                        self._logmsg("  SEO applied to local files. (No CSV to export)", "success")

                    compress_stats = compress_stats_result
                else:
                    # الطريقة القديمة
                    imgs = []
                    if os.path.exists(src):
                        for root, _, files in os.walk(src):
                            for fn in files:
                                if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')):
                                    imgs.append(os.path.join(root, fn))

                    if not imgs:
                        self._logmsg("No images to compress!   لا توجد صور للضغط!", "warning")
                    else:
                        done = 0
                        total = len(imgs)
                        for ip in imgs:
                            if self.should_stop:
                                self._finish(False)
                                return
                            try:
                                compressor._compress_single_legacy(ip)
                                self._logmsg(f"  OK  {os.path.relpath(ip, src)}", "info")
                            except Exception as e:
                                compressor.stats['failed'] += 1
                                self._logmsg(f"  FAIL  {os.path.basename(ip)}: {e}", "error")
                            done += 1
                            self._set_pbar(50 + int((done / max(total, 1)) * 40))
                            self._set_detail(f"Compressed {done}/{total}")

                    compress_stats = compressor.stats

                self._set_pbar(90)

                if compress_stats.get('original_size', 0) > 0:
                    sav = compress_stats['original_size'] - compress_stats['compressed_size']
                    pct = (sav / compress_stats['original_size']) * 100
                    self._logmsg(f"\nCompression done:", "success")
                    self._logmsg(f"  Before: {Formatter._format_size(compress_stats['original_size'])}", "info")
                    self._logmsg(f"  After:  {Formatter._format_size(compress_stats['compressed_size'])}", "info")
                    self._logmsg(f"  Saved:  {Formatter._format_size(sav)} ({pct:.1f}%)", "success")

            # 4. تقرير
            self._set_pbar(95)
            if self.input_source.get() == "csv":
                rdir = os.path.dirname(self.csv_path.get())
            else:
                rdir = comp_dir
            rpath = os.path.join(rdir, "report.txt")
            ReportGenerator(output_path=rpath).generate(products, download_stats, compress_stats, {})
            self._logmsg(f"\nReport saved: {rpath}", "info")
            
            # Clean up temp_extract_dir if it exists
            if temp_extract_dir and os.path.exists(temp_extract_dir):
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception as e:
                    pass

            el = time.time() - t0
            self._logmsg(f"\n{'=' * 50}", "header")
            self._logmsg(f"DONE in {int(el//60)}m {int(el%60)}s   تم في {int(el//60)} دقيقة و {int(el%60)} ثانية", "header")
            self._finish(True)

        except Exception as e:
            self._logmsg(f"\nERROR: {e}", "error")
            import traceback
            self._logmsg(traceback.format_exc(), "error")
            self._finish(False)

    # ─── مساعدات thread-safe ───
    def _logmsg(self, msg, tag="info"):
        self.log_queue.put((msg, tag))

    def _poll_log(self):
        while not self.log_queue.empty():
            try:
                item = self.log_queue.get_nowait()
                # WordPress messages have 3 elements (msg, tag, "wp")
                if len(item) == 3 and item[2] == "wp":
                    msg, tag, _ = item
                    if hasattr(self, 'wp_log'):
                        self.wp_log.config(state=tk.NORMAL)
                        self.wp_log.insert(tk.END, msg + "\n", tag)
                        self.wp_log.see(tk.END)
                        self.wp_log.config(state=tk.DISABLED)
                else:
                    msg, tag = item[0], item[1]
                    self.log.config(state=tk.NORMAL)
                    self.log.insert(tk.END, msg + "\n", tag)
                    self.log.see(tk.END)
                    self.log.config(state=tk.DISABLED)
            except queue.Empty:
                break
        self.root.after(100, self._poll_log)

    def _set_status(self, t):
        self.root.after(0, lambda: self.status_lbl.config(text=t, fg=self.TEXT))

    def _set_pbar(self, v):
        self.root.after(0, lambda: self.pbar.configure(value=v))

    def _set_detail(self, t):
        self.root.after(0, lambda: self.detail_lbl.config(text=t))

    def run(self):
        self.root.mainloop()


    # ═══════════════════════════════════════════════════════════
    # WordPress Tab — واجهة ووردبريس (ضغط + SEO بدون API)
    # ═══════════════════════════════════════════════════════════

    def _build_wp_tab(self, parent):
        """بناء واجهة WordPress/WooCommerce."""
        # ─── Scrollable ───
        wp_canvas = tk.Canvas(parent, bg=self.BG_DARK, highlightthickness=0)
        wp_sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=wp_canvas.yview)
        self.wp_content = tk.Frame(wp_canvas, bg=self.BG_DARK)
        self.wp_content.bind("<Configure>", lambda e: wp_canvas.configure(scrollregion=wp_canvas.bbox("all")))
        wp_canvas.create_window((0, 0), window=self.wp_content, anchor="nw")
        wp_canvas.configure(yscrollcommand=wp_sb.set)
        wp_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        wp_sb.pack(side=tk.RIGHT, fill=tk.Y)

        # متغيرات WordPress
        self.wp_input_source = tk.StringVar(value="csv")
        self.wp_local_files = []
        self.wp_csv_path = tk.StringVar()
        self.wp_input_folder = tk.StringVar()
        self.wp_compress_folder = tk.StringVar()
        self.wp_quality = tk.IntVar(value=85)
        self.wp_is_running = False
        self.wp_should_stop = False

        # ═══ 1. مصدر الإدخال ═══
        c1 = self._wp_card("Input Source   -   مصدر الإدخال")
        src_row = tk.Frame(c1, bg=self.BG_CARD)
        src_row.pack(fill=tk.X, pady=(0, 5))
        tk.Radiobutton(src_row, text="WooCommerce CSV", variable=self.wp_input_source, value="csv",
                       font=("Segoe UI", 10, "bold"), fg=self.TEXT, bg=self.BG_CARD,
                       selectcolor=self.BG_INPUT, activebackground=self.BG_CARD,
                       activeforeground=self.CYAN, anchor="w",
                       command=self._wp_on_source_change).pack(side=tk.LEFT)
        tk.Radiobutton(src_row, text="Direct Images / Archive (ZIP/RAR)", variable=self.wp_input_source, value="local",
                       font=("Segoe UI", 10, "bold"), fg=self.TEXT, bg=self.BG_CARD,
                       selectcolor=self.BG_INPUT, activebackground=self.BG_CARD,
                       activeforeground=self.CYAN, anchor="w",
                       command=self._wp_on_source_change).pack(side=tk.LEFT, padx=15)

        tk.Frame(c1, bg=self.BG_INPUT, height=1).pack(fill=tk.X, pady=5)

        # صف CSV
        self.wp_csv_row = tk.Frame(c1, bg=self.BG_CARD)
        self.wp_csv_row.pack(fill=tk.X, pady=2)
        self._file_row(self.wp_csv_row, self.wp_csv_path, "Choose WooCommerce CSV   اختر ملف", self._wp_browse_csv)

        # صف صور مباشرة
        self.wp_local_row = tk.Frame(c1, bg=self.BG_CARD)
        self.wp_local_lbl = tk.Label(self.wp_local_row, text="No files selected", font=("Segoe UI", 10),
                                     fg=self.TEXT_DIM, bg=self.BG_CARD, anchor="w")
        self.wp_local_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(self.wp_local_row, text="📂 Choose Images/ZIP", font=("Segoe UI", 9, "bold"),
                  bg=self.ACCENT, fg="white", relief=tk.FLAT, padx=10, pady=3,
                  cursor="hand2", command=self._wp_browse_local,
                  activebackground=self.ACCENT_HOVER).pack(side=tk.RIGHT)

        # ═══ 2. مجلدات الحفظ ═══
        c2 = self._wp_card("Save Location   -   مكان الحفظ")

        self.wp_input_frame = tk.Frame(c2, bg=self.BG_CARD)
        self.wp_input_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.wp_input_frame, text="Images Folder   مجلد الصور (الإدخال):",
                 font=("Segoe UI", 10), fg=self.CYAN, bg=self.BG_CARD, anchor="e").pack(fill=tk.X)
        self._file_row(self.wp_input_frame, self.wp_input_folder, "Choose Folder", self._wp_browse_input, is_folder=True)

        self.wp_comp_frame = tk.Frame(c2, bg=self.BG_CARD)
        self.wp_comp_frame.pack(fill=tk.X, pady=3)
        tk.Label(self.wp_comp_frame, text="Compressed Folder   مجلد الصور المضغوطة:",
                 font=("Segoe UI", 10), fg=self.CYAN, bg=self.BG_CARD, anchor="e").pack(fill=tk.X)
        self._file_row(self.wp_comp_frame, self.wp_compress_folder, "Choose Folder", self._wp_browse_comp, is_folder=True)

        # ═══ 3. إعدادات ═══
        c3 = self._wp_card("Settings   -   الإعدادات")
        srow = tk.Frame(c3, bg=self.BG_CARD)
        srow.pack(fill=tk.X, pady=4)
        tk.Label(srow, text="Compression Quality   جودة الضغط:", font=("Segoe UI", 10),
                 fg=self.TEXT, bg=self.BG_CARD).pack(side=tk.RIGHT, padx=(10, 0))
        self.wp_qlbl = tk.Label(srow, text="85%", font=("Segoe UI", 10, "bold"),
                                fg=self.GREEN, bg=self.BG_CARD, width=4)
        self.wp_qlbl.pack(side=tk.RIGHT, padx=5)
        tk.Scale(srow, from_=100, to=30, orient=tk.HORIZONTAL, variable=self.wp_quality,
                 showvalue=False, bg=self.BG_CARD, fg=self.TEXT, troughcolor=self.BG_INPUT,
                 highlightthickness=0, length=150, sliderrelief=tk.FLAT,
                 command=lambda v: self.wp_qlbl.config(text=f"{v}%")).pack(side=tk.RIGHT)

        # ═══ Info ═══
        info_card = self._wp_card("ℹ️  WordPress Mode   -   وضع ووردبريس")
        info_text = (
            "This mode processes images locally for WordPress/WooCommerce.\n"
            "هذا الوضع يعالج الصور محلياً لووردبريس — بدون API.\n\n"
            "Outputs   المخرجات:\n"
            "  • Compressed WebP images with SEO filenames\n"
            "  • WooCommerce CSV with updated image names\n"
            "  • Alt Text reference (CSV + HTML) for manual copy\n"
            "  • Optimization report"
        )
        tk.Label(info_card, text=info_text, font=("Segoe UI", 9), fg=self.TEXT_DIM,
                 bg=self.BG_CARD, justify=tk.LEFT, anchor="w").pack(fill=tk.X)

        # ═══ أزرار ═══
        btns = tk.Frame(self.wp_content, bg=self.BG_DARK)
        btns.pack(fill=tk.X, pady=10, padx=5)

        self.wp_start_btn = tk.Button(btns, text="START   تشغيل   🚀",
                                      font=("Segoe UI", 14, "bold"),
                                      bg=self.GREEN, fg="white", relief=tk.FLAT,
                                      padx=30, pady=10, cursor="hand2",
                                      command=self._wp_start, activebackground="#27ae60")
        self.wp_start_btn.pack(side=tk.RIGHT, padx=8)

        self.wp_stop_btn = tk.Button(btns, text="STOP   إيقاف   ⏹",
                                     font=("Segoe UI", 14, "bold"),
                                     bg="#e74c3c", fg="white", relief=tk.FLAT,
                                     padx=30, pady=10, cursor="hand2",
                                     command=self._wp_stop, activebackground="#c0392b",
                                     state=tk.DISABLED)
        self.wp_stop_btn.pack(side=tk.RIGHT, padx=8)

        tk.Button(btns, text="Open Folder   فتح المجلد   📁",
                  font=("Segoe UI", 11), bg=self.BG_INPUT, fg=self.TEXT,
                  relief=tk.FLAT, padx=15, pady=10, cursor="hand2",
                  command=self._wp_open_folder, activebackground=self.BG_CARD
                  ).pack(side=tk.LEFT, padx=8)

        # ═══ شريط التقدم ═══
        pf = tk.Frame(self.wp_content, bg=self.BG_DARK)
        pf.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.wp_status_lbl = tk.Label(pf, text="Ready   جاهز...",
                                      font=("Segoe UI", 10), fg=self.TEXT_DIM,
                                      bg=self.BG_DARK, anchor="e")
        self.wp_status_lbl.pack(fill=tk.X)

        self.wp_pbar = ttk.Progressbar(pf, style="G.Horizontal.TProgressbar",
                                        mode='determinate', maximum=100)
        self.wp_pbar.pack(fill=tk.X, pady=4)

        self.wp_detail_lbl = tk.Label(pf, text="", font=("Consolas", 9),
                                      fg=self.TEXT_DIM, bg=self.BG_DARK, anchor="e")
        self.wp_detail_lbl.pack(fill=tk.X)

        # ═══ سجل ═══
        lc = self._wp_card("Log   السجل")
        self.wp_log = scrolledtext.ScrolledText(lc, height=10, font=("Consolas", 10),
                                                 bg="#0a0a1a", fg=self.GREEN,
                                                 insertbackground=self.GREEN,
                                                 relief=tk.FLAT, borderwidth=8,
                                                 wrap=tk.WORD, state=tk.DISABLED)
        self.wp_log.pack(fill=tk.BOTH, expand=True)
        self.wp_log.tag_config("error", foreground="#e74c3c")
        self.wp_log.tag_config("warning", foreground="#f39c12")
        self.wp_log.tag_config("success", foreground="#2ecc71")
        self.wp_log.tag_config("info", foreground="#3498db")
        self.wp_log.tag_config("header", foreground="#00d2d3", font=("Consolas", 10, "bold"))

        self._wp_on_source_change()

    def _wp_card(self, title):
        """بطاقة UI لتبويب WordPress."""
        WP_ACCENT = "#3b82f6"  # أزرق لتمييز ووردبريس عن شوبيفاي
        c = tk.Frame(self.wp_content, bg=self.BG_CARD, padx=15, pady=10,
                     highlightbackground=self.BG_INPUT, highlightthickness=1)
        c.pack(fill=tk.X, pady=5, padx=5)
        tk.Label(c, text=title, font=("Segoe UI", 12, "bold"),
                 fg=WP_ACCENT, bg=self.BG_CARD, anchor="e").pack(fill=tk.X)
        tk.Frame(c, bg=WP_ACCENT, height=1).pack(fill=tk.X, pady=(3, 6))
        return c

    # ─── WordPress Events ───
    def _wp_on_source_change(self):
        src = self.wp_input_source.get()
        if src == "csv":
            self.wp_csv_row.pack(fill=tk.X, pady=2)
            self.wp_local_row.pack_forget()
            self.wp_input_frame.pack(fill=tk.X, pady=3)
        else:
            self.wp_local_row.pack(fill=tk.X, pady=2)
            self.wp_csv_row.pack_forget()
            self.wp_input_frame.pack(fill=tk.X, pady=3)

    def _wp_browse_csv(self):
        p = filedialog.askopenfilename(title="Choose WooCommerce CSV",
                                        filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if p:
            self.wp_csv_path.set(p)
            base = os.path.dirname(p)
            if not self.wp_input_folder.get():
                self.wp_input_folder.set(os.path.join(base, "downloaded_images"))
            if not self.wp_compress_folder.get():
                self.wp_compress_folder.set(os.path.join(base, "wp_compressed_images"))

    def _wp_browse_local(self):
        files = filedialog.askopenfilenames(title="Choose Images or Archive",
                                            filetypes=[("Images & Archives", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.zip *.rar"), ("All", "*.*")])
        if files:
            self.wp_local_files = list(files)
            if len(self.wp_local_files) == 1:
                self.wp_local_lbl.config(text=f"Selected: {os.path.basename(self.wp_local_files[0])}")
            else:
                self.wp_local_lbl.config(text=f"Selected {len(self.wp_local_files)} files")
            base = os.path.dirname(self.wp_local_files[0])
            if not self.wp_compress_folder.get():
                self.wp_compress_folder.set(os.path.join(base, "wp_compressed_images"))

    def _wp_browse_input(self):
        p = filedialog.askdirectory(title="Choose Images Folder")
        if p: self.wp_input_folder.set(p)

    def _wp_browse_comp(self):
        p = filedialog.askdirectory(title="Choose Compressed Folder")
        if p: self.wp_compress_folder.set(p)

    def _wp_open_folder(self):
        for p in [self.wp_compress_folder.get(), self.wp_input_folder.get()]:
            if p and os.path.exists(p):
                os.startfile(p)
                return

    # ─── WordPress Start/Stop ───
    def _wp_start(self):
        if self.wp_input_source.get() == "csv":
            if not self.wp_csv_path.get() or not os.path.exists(self.wp_csv_path.get()):
                messagebox.showwarning("Warning", "Choose a valid WooCommerce CSV!\nاختر ملف CSV صحيح!")
                return
        else:
            if not self.wp_local_files and not self.wp_input_folder.get():
                messagebox.showwarning("Warning", "Choose images or folder!\nاختر صور أو مجلد!")
                return
        if not self.wp_compress_folder.get():
            messagebox.showwarning("Warning", "Choose compressed folder!\nاختر مجلد الضغط!")
            return

        self.wp_is_running = True
        self.wp_should_stop = False
        self.wp_start_btn.config(state=tk.DISABLED, bg="#7f8c8d")
        self.wp_stop_btn.config(state=tk.NORMAL)
        self.wp_pbar['value'] = 0
        self.wp_log.config(state=tk.NORMAL)
        self.wp_log.delete(1.0, tk.END)
        self.wp_log.config(state=tk.DISABLED)

        threading.Thread(target=self._wp_run, daemon=True).start()

    def _wp_stop(self):
        if self.wp_is_running:
            self.wp_should_stop = True
            self._wp_logmsg("STOPPED — will finish current image then stop", "warning")

    def _wp_finish(self, ok=True):
        self.wp_is_running = False
        self.wp_should_stop = False
        self.root.after(0, lambda: self.wp_start_btn.config(state=tk.NORMAL, bg=self.GREEN))
        self.root.after(0, lambda: self.wp_stop_btn.config(state=tk.DISABLED))
        if ok:
            self.root.after(0, lambda: self.wp_status_lbl.config(text="Done!   اكتملت العملية بنجاح! 🎉", fg=self.GREEN))
            self.root.after(0, lambda: self.wp_pbar.configure(value=100))
        else:
            self.root.after(0, lambda: self.wp_status_lbl.config(text="Stopped   تم الإيقاف 🛑", fg=self.YELLOW))

    # ─── WordPress Main Process ───
    def _wp_run(self):
        try:
            comp_dir = self.wp_compress_folder.get()
            t0 = time.time()
            products = {}
            temp_extract_dir = ""
            input_dir = self.wp_input_folder.get()

            # 1. قراءة الإدخال
            if self.wp_input_source.get() == "csv":
                self._wp_logmsg("=" * 50, "header")
                self._wp_logmsg("Reading WooCommerce CSV...   قراءة ملف WooCommerce CSV...", "header")
                self._wp_set_status("Reading CSV...")
                self._wp_set_pbar(5)

                parser = WooCommerceCSVParser(self.wp_csv_path.get())
                products = parser.parse()
                if not products:
                    self._wp_logmsg("ERROR: No products found!", "error")
                    self._wp_finish(False)
                    return

                total_imgs = sum(len(p['images']) for p in products.values())
                self._wp_logmsg(f"Found {len(products)} products, {total_imgs} images", "success")
                self._wp_set_pbar(10)

                # لو مفيش مجلد إدخال — أنشئ واحد
                if not input_dir:
                    input_dir = os.path.join(os.path.dirname(self.wp_csv_path.get()), "downloaded_images")

            else:
                # صور مباشرة
                self._wp_logmsg("=" * 50, "header")
                self._wp_logmsg("Preparing local files...", "header")
                self._wp_set_status("Preparing files...")
                self._wp_set_pbar(5)

                temp_extract_dir = os.path.join(comp_dir, "_wp_temp_extract")
                os.makedirs(temp_extract_dir, exist_ok=True)
                input_dir = temp_extract_dir

                for fpath in self.wp_local_files:
                    ext = fpath.lower().split('.')[-1]
                    if ext == 'zip':
                        self._wp_logmsg(f"Extracting ZIP: {os.path.basename(fpath)}", "info")
                        try:
                            with zipfile.ZipFile(fpath, 'r') as z:
                                z.extractall(temp_extract_dir)
                        except Exception as e:
                            self._wp_logmsg(f"Error: {e}", "error")
                    elif ext == 'rar' and RAR_AVAILABLE:
                        self._wp_logmsg(f"Extracting RAR: {os.path.basename(fpath)}", "info")
                        try:
                            with rarfile.RarFile(fpath) as r:
                                r.extractall(temp_extract_dir)
                        except Exception as e:
                            self._wp_logmsg(f"Error: {e}", "error")
                    elif ext in ('jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'avif'):
                        base_name = os.path.splitext(os.path.basename(fpath))[0]
                        safe = re.sub(r'[<>:"/\\|?*]', '_', base_name).strip('. ') or 'unknown'
                        target = os.path.join(temp_extract_dir, safe)
                        os.makedirs(target, exist_ok=True)
                        shutil.copy2(fpath, os.path.join(target, os.path.basename(fpath)))

                # بناء products من المجلدات
                for root, dirs, files in os.walk(temp_extract_dir):
                    rel = os.path.relpath(root, temp_extract_dir)
                    if rel == '.':
                        continue
                    imgs = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.avif'))]
                    if not imgs:
                        continue
                    handle = rel.replace('\\', '/').split('/')[0]
                    if handle not in products:
                        products[handle] = {
                            'name': handle.replace('-', ' ').replace('_', ' ').title(),
                            'sku': '', 'categories': '', 'tags': '',
                            'short_description': '', 'images': [],
                        }

                if not products:
                    self._wp_logmsg("No valid images found!", "error")
                    self._wp_finish(False)
                    return

                self._wp_logmsg(f"Found {len(products)} products", "success")
                self._wp_set_pbar(10)

            if self.wp_should_stop:
                self._wp_finish(False)
                return

            # 2. ضغط + SEO
            self._wp_logmsg("\n" + "=" * 50, "header")
            self._wp_logmsg(f"WordPress SEO Compressing (quality: {self.wp_quality.get()}%)...", "header")
            self._wp_set_status("SEO Compressing...")

            csv_dir = os.path.dirname(self.wp_csv_path.get()) if self.wp_input_source.get() == "csv" else comp_dir
            seo_log_path = os.path.join(csv_dir, 'wp_seo_optimization_log.csv')
            seo_logger_inst = WPSEOLogger(log_path=seo_log_path)

            compressor = WordPressImageCompressor(
                input_dir=input_dir, output_dir=comp_dir,
                quality=self.wp_quality.get()
            )

            def wp_progress(done, total):
                if self.wp_should_stop:
                    return False
                self._wp_set_pbar(15 + int((done / max(total, 1)) * 55))
                self._wp_set_detail(f"SEO Compressing {done}/{total}")
                self.root.update_idletasks()
                return True

            compress_stats = compressor.compress_all_seo(products, seo_logger_inst, progress_callback=wp_progress)

            seo_logger_inst.save()
            self._wp_logmsg(f"SEO Log saved: {seo_log_path}", "success")
            self._wp_logmsg(f"{seo_logger_inst.get_summary()}", "info")

            if compress_stats.get('original_size', 0) > 0:
                sav = compress_stats['original_size'] - compress_stats['compressed_size']
                pct = (sav / compress_stats['original_size']) * 100
                self._wp_logmsg(f"\nCompression done:", "success")
                self._wp_logmsg(f"  Before: {WordPressImageCompressor._format_size(compress_stats['original_size'])}", "info")
                self._wp_logmsg(f"  After:  {WordPressImageCompressor._format_size(compress_stats['compressed_size'])}", "info")
                self._wp_logmsg(f"  Saved:  {WordPressImageCompressor._format_size(sav)} ({pct:.1f}%)", "success")

            self._wp_set_pbar(75)

            # 3. تصدير CSV محسّن
            if self.wp_input_source.get() == "csv":
                seo_csv_path = os.path.join(csv_dir, 'products_wp_optimized.csv')
                exporter = WooCommerceCSVExporter(
                    original_csv=self.wp_csv_path.get(),
                    seo_map=compressor.seo_map,
                    output_path=seo_csv_path
                )
                exporter.export()
                self._wp_logmsg(f"WP CSV saved: {seo_csv_path}", "success")

            self._wp_set_pbar(85)

            # 4. تصدير Alt Text Reference
            alt_exporter = WordPressAltTextExporter(
                seo_map=compressor.seo_map,
                products=products,
                output_dir=csv_dir
            )
            alt_exporter.export_all()
            self._wp_logmsg(f"Alt Text reference exported to {csv_dir}", "success")

            self._wp_set_pbar(92)

            # 5. تقرير
            rpath = os.path.join(csv_dir, "wp_report.txt")
            WordPressReportGenerator(output_path=rpath).generate(products, compress_stats)
            self._wp_logmsg(f"Report saved: {rpath}", "info")

            # تنظيف
            if temp_extract_dir and os.path.exists(temp_extract_dir):
                try:
                    shutil.rmtree(temp_extract_dir)
                except Exception:
                    pass

            el = time.time() - t0
            self._wp_logmsg(f"\n{'=' * 50}", "header")
            self._wp_logmsg(f"DONE in {int(el//60)}m {int(el%60)}s", "header")
            self._wp_finish(True)

        except Exception as e:
            self._wp_logmsg(f"\nERROR: {e}", "error")
            import traceback
            self._wp_logmsg(traceback.format_exc(), "error")
            self._wp_finish(False)

    # ─── WordPress thread-safe helpers ───
    def _wp_logmsg(self, msg, tag="info"):
        self.log_queue.put((msg, tag, "wp"))

    def _wp_set_status(self, t):
        self.root.after(0, lambda: self.wp_status_lbl.config(text=t, fg=self.TEXT))

    def _wp_set_pbar(self, v):
        self.root.after(0, lambda: self.wp_pbar.configure(value=v))

    def _wp_set_detail(self, t):
        self.root.after(0, lambda: self.wp_detail_lbl.config(text=t))


if __name__ == '__main__':
    app = ShopifyImageGUI()
    app.run()
