#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
واجهة رسومية لأداة تحميل وضغط صور منتجات شوبيفاي
Shopify Bulk Image Tool - GUI (بدون API)

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

from shopify_image_downloader import (
    ShopifyCSVParser, ImageDownloader, ImageCompressor,
    ReportGenerator, ImageDownloader as Formatter,
    ShopifyCSVExporter, SEO_AVAILABLE
)

if SEO_AVAILABLE:
    from seo_helpers import SEOLogger


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
        self.root.title("Shopify Bulk Image Tool")
        self.root.geometry("880x720")
        self.root.minsize(800, 650)
        self.root.configure(bg=self.BG_DARK)

        # متغيرات
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
        tk.Label(hdr, text="Shopify Bulk Image Tool   -   " + "أداة صور شوبيفاي بالجملة",
                 font=("Segoe UI", 14, "bold"), fg="white", bg=self.ACCENT).pack(pady=10)

        # ─── Scrollable ───
        canvas = tk.Canvas(self.root, bg=self.BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=canvas.yview)
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

        # ═══ 2. ملف CSV ═══
        self.csv_card = self._card("CSV File   -   ملف CSV من شوبيفاي")
        self._file_row(self.csv_card, self.csv_path, "Choose CSV File   اختر ملف", self._browse_csv)

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
    def _on_mode_change(self):
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
        if not self.csv_path.get() or not os.path.exists(self.csv_path.get()):
            messagebox.showwarning("Warning", "Choose a valid CSV file first!\nاختر ملف CSV صحيح!")
            return
        if not self.download_folder.get():
            messagebox.showwarning("Warning", "Choose download folder!\nاختر مجلد التحميل!")
            return
        if self.mode.get() in ("download_compress", "compress_only") and not self.compress_folder.get():
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

            # 1. قراءة CSV
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

            if self.should_stop:
                self._finish(False)
                return

            download_stats = {}
            compress_stats = {}

            # 2. تحميل
            if mode in ("download_compress", "download_only"):
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
                    csv_dir = os.path.dirname(self.csv_path.get())
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
                    seo_csv_path = os.path.join(csv_dir, 'products_seo_optimized.csv')
                    exporter = ShopifyCSVExporter(
                        original_csv=self.csv_path.get(),
                        seo_map=compressor.seo_map,
                        output_path=seo_csv_path
                    )
                    exporter.export()
                    self._logmsg(f"  SEO CSV saved: {seo_csv_path}", "success")

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
            rdir = os.path.dirname(self.csv_path.get())
            rpath = os.path.join(rdir, "report.txt")
            ReportGenerator(output_path=rpath).generate(products, download_stats, compress_stats, {})
            self._logmsg(f"\nReport saved: {rpath}", "info")

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
                msg, tag = self.log_queue.get_nowait()
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


if __name__ == '__main__':
    app = ShopifyImageGUI()
    app.run()
