"""Eye Contact UI (tkinter). Ishga tushirish: EyeContact.bat (runtime\\python\\pythonw.exe -m eyecontact.gui).

Portativ paket: Python, ffmpeg va Maxine SDK runtime\\ ichida, o'rnatish kerak emas. Ishga tushishda doctor():
GPU/drayver/SDK mosligi tekshiriladi; paketdagi SDK boshqa GPU arxitekturasiga bo'lsa tizimdagi SDK ishlatiladi.

Har video alohida jarayonda (`python -m eyecontact.cli --resume --progress`) ishlanadi: UI qotmaydi, Maxine yiqilsa
UI yopilmaydi, "To'xtatish" jarayon daraxtini o'ldiradi va keyingi safar --resume uzilgan joydan davom etadi.
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from . import theme
from .theme import C, F, px, sp
from .widgets import Button, Checkbox, DoctorBanner, LogPanel, Panel, PathField, QueueList, Slider, split_doctor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(ROOT, "gui_settings.json")
VIDEO_TYPES = [("Video", "*.mp4 *.mov *.mkv *.m4v *.MP4 *.MOV *.MKV"), ("Hammasi", "*.*")]
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def dpi_aware():
    """HiDPI ekranda (125-200% masshtab) matn xira chiqmasligi uchun. Tk() dan oldin chaqiriladi."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


ARCHS = (("blackwell", r"RTX\s*(PRO\s*)?5\d{3}|RTX PRO|B\d{3}|Blackwell"), ("ada", r"RTX\s*4\d{3}|RTX\s*\d{4}\s*Ada|Ada|L4\b|L40"),
         ("ampere", r"RTX\s*3\d{3}|RTX A\d{4}|A10\b|A40|A100|A30"), ("turing", r"RTX\s*2\d{3}|GTX 16\d{2}|Quadro RTX|T4\b|T1000|T600"))
MIN_DRIVER = 570.0


def gpu_info():
    """(nom, driver) yoki (None, None). nvidia-smi driver bilan keladi."""
    import re
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                             capture_output=True, encoding="utf-8", errors="replace", timeout=15, creationflags=NO_WINDOW).stdout
        name, drv = [s.strip() for s in out.splitlines()[0].split(",")[:2]]
        return name, float(re.match(r"[\d.]+", drv).group(0))
    except Exception:
        return None, None


def gpu_arch(name):
    import re
    for arch, pat in ARCHS:
        if re.search(pat, name, re.I):
            return arch
    return None


def doctor():
    """Ishga tushishda tekshiruv. Qaytaradi (ok, xabar, sdk_dir yoki None)."""
    from . import maxine, video_io
    name, drv = gpu_info()
    if not name:
        return False, ("NVIDIA GPU yoki drayver topilmadi (nvidia-smi ishlamadi).\n"
                       "Dastur NVIDIA RTX video karta talab qiladi. Drayverni o'rnating: nvidia.com/drivers"), None
    if drv and drv < MIN_DRIVER:
        return False, f"NVIDIA drayver eski: {drv:g}. Kamida {MIN_DRIVER:.0f} kerak. Yangilang: nvidia.com/drivers", None
    arch = gpu_arch(name)
    bundled = os.path.join(ROOT, "runtime", "maxine")
    bundled_arch = ""
    try:
        with open(os.path.join(bundled, "ARCH.txt"), encoding="utf-8") as f:
            bundled_arch = f.read().strip()
    except OSError:
        pass
    candidates = []
    if os.path.exists(os.path.join(bundled, "nvARPose.dll")) and (not arch or arch == bundled_arch):
        candidates.append(bundled)
    if os.path.exists(os.path.join(maxine._SYSTEM, "nvARPose.dll")):
        candidates.append(maxine._SYSTEM)
    if os.path.exists(os.path.join(bundled, "nvARPose.dll")) and bundled not in candidates:
        candidates.append(bundled)      # arxitektura noma'lum/boshqa: baribir urinib ko'ramiz
    last_err = ""
    for d in candidates:
        try:
            g = maxine.GazeRedirector(640, 360, model_dir=os.path.join(d, "models"), sdk_dir=d)
            g.close()
            return True, f"{name}, drayver {drv:g}, Maxine SDK: {'paket ichida' if d == bundled else 'tizimda'}", d
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
    hint = (f"Paket ichidagi Maxine SDK «{bundled_arch or '?'}» uchun, sizning GPU: {name} ({arch or 'noma’lum'}).\n"
            f"«SDK_ornatish.bat» ni ishga tushiring: u GPU ga mos SDK ni yuklab o'rnatadi (internet, administrator).")
    return False, f"Maxine SDK ishga tushmadi: {last_err or 'SDK topilmadi'}\n\n{hint}", None


def python_exe():
    exe = sys.executable
    return exe[:-len("pythonw.exe")] + "python.exe" if exe.lower().endswith("pythonw.exe") else exe


def fmt_time(sec):
    sec = int(max(0, sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def fmt_dur(sec):
    s = int(round(sec))
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h} soat {m:02d} min" if h else (f"{m} min {s:02d} s" if m else f"{s} s")


def fmt_size(b):
    return f"{b / 1e9:.1f} GB" if b >= 1e9 else f"{b / 1e6:.0f} MB"


def describe(path):
    """QueueRow caption: "1920×1080 · 13 min 19 s · 2.4 GB" (ffprobe). O'qilmasa faqat hajm."""
    parts = []
    try:
        from .video_io import FFPROBE
        out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height:format=duration", "-of", "json", path],
                             capture_output=True, encoding="utf-8", errors="replace", timeout=30, creationflags=NO_WINDOW).stdout
        d = json.loads(out or "{}")
        st = (d.get("streams") or [{}])[0]
        if st.get("width"):
            parts.append(f"{st['width']}×{st['height']}")
        dur = float((d.get("format") or {}).get("duration") or 0)
        if dur:
            parts.append(fmt_dur(dur))
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    try:
        parts.append(fmt_size(os.path.getsize(path)))
    except OSError:
        pass
    return " · ".join(parts)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Eye Contact — nigohni kameraga qaratish")
        theme.init(root)                                             # tokenlar, shriftlar, DPI masshtabi
        self.k = k = theme.k
        w = min(int(960 * k), int(root.winfo_screenwidth() * 0.9))
        h = min(int(780 * k), int(root.winfo_screenheight() * 0.88))
        root.geometry(f"{w}x{h}")
        root.minsize(min(int(820 * k), w), min(int(620 * k), h))
        self.events = queue.Queue()
        self.proc = None
        self.worker = None
        self.stop_flag = False
        self.last_output = None
        s = self._load()
        self.out_dir = tk.StringVar(value=s.get("out_dir", ""))
        self.lid_open = tk.DoubleVar(value=s.get("lid_open", 0.5))
        self.hevc = tk.BooleanVar(value=s.get("hevc", False))
        self.sdk_dir = None
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.pump)
        self.btn_start.config(state="disabled")
        self.btn_prev.config(state="disabled")
        self.status.config(text="Tekshirilmoqda: GPU, drayver, Maxine SDK…")
        threading.Thread(target=lambda: self.events.put(("doctor",) + doctor()), daemon=True).start()

    # ---------- UI ----------
    def _build(self):
        """design-system/README.md: oyna cheti space-6, panellar orasida space-5, panel ichida space-4.
        Tugma canvaslari focus-ring uchun har tomonda RING px zaxira oladi, bo'shliqlar shunga tuzatilgan."""
        root, s100, ring = self.root, C["surface-100"], px(theme.RING)
        edge, gap3 = sp(6) - ring, max(0, sp(3) - 2 * ring)

        self.banner = DoctorBanner(root)                      # faqat doctor() muammo topsa pack qilinadi

        self.toolbar = tk.Frame(root, bg=s100)                # Toolbar
        self.toolbar.pack(fill="x", padx=edge, pady=sp(4) - ring)
        left = tk.Frame(self.toolbar, bg=s100)
        left.pack(side="left")
        Button(left, "Video qoʻshish", "secondary", self.add_files).pack(side="left")
        Button(left, "Tanlanganini olib tashlash", "ghost", self.remove_selected).pack(side="left", padx=(gap3, 0))
        Button(left, "Roʻyxatni tozalash", "ghost", self.clear).pack(side="left", padx=(gap3, 0))
        right = tk.Frame(self.toolbar, bg=s100)
        right.pack(side="right", fill="x", expand=True, padx=(max(0, sp(5) - 2 * ring), 0))
        Button(right, "Koʻrib chiqish…", "secondary", self.pick_out).pack(side="right")
        self.path = PathField(right, self.out_dir, "boʻsh boʻlsa video yonida")
        self.path.pack(side="right", fill="x", expand=True, padx=(0, gap3))
        tk.Frame(root, bg=C["border"], height=max(1, round(theme.k))).pack(fill="x")

        body = tk.Frame(root, bg=s100)
        body.pack(fill="both", expand=True, padx=sp(6), pady=(sp(5), sp(6)))

        # pastdan yuqoriga: Jurnal, amallar, sozlamalar; qolgan joy navbatga
        self.log = LogPanel(body, "Jurnal", lines=5)
        self.log.pack(side="bottom", fill="x")
        act = tk.Frame(body, bg=s100)
        act.pack(side="bottom", fill="x", pady=(sp(4) - ring, sp(5) - ring), padx=(0, 0))
        self.btn_start = Button(act, "Boshlash", "primary", self.start)
        self.btn_start.pack(side="left", padx=(0, gap3))
        self.btn_prev = Button(act, "Preview (30 s, yonma-yon)", "secondary", lambda: self.start(preview=True))
        self.btn_prev.pack(side="left", padx=(0, gap3))
        self.btn_stop = Button(act, "Toʻxtatish", "secondary", self.stop, state="disabled")
        self.btn_stop.pack(side="left")
        self.btn_open = Button(act, "Natija papkasini ochish", "secondary", self.open_output, state="disabled")
        self.btn_open.pack(side="right")
        self.status = tk.Label(act, text="Video qoʻshing va «Boshlash» ni bosing.", font=F["caption"],
                               fg=C["ink-secondary"], bg=s100, anchor="w")
        self.status.pack(side="left", fill="x", expand=True, padx=(sp(3), sp(3)))

        sm = px(Slider.MARGIN)                                 # slayder thumb'i panel padding'iga chiqadi
        settings = Panel(body, fill="surface-200", border="border", radius="lg", pad=(sp(4) - sm, sp(4)), fit=True)
        settings.pack(side="bottom", fill="x", pady=(sp(5), 0))
        sb = settings.body
        Slider(sb, self.lid_open, "Tuzatish kuchi", "0 · qovoq saqlanadi", "1 · kuchli tuzatish").grid(
            row=0, column=0, sticky="ew")
        Checkbox(sb, self.hevc, "HEVC", caption="H.265. DaVinci bepul versiyasi ochmaydi, belgilanmasa H.264").grid(
            row=0, column=1, sticky="nw", padx=(sp(6), sm))
        sb.columnconfigure(0, weight=1)

        head = tk.Frame(body, bg=s100)
        head.pack(side="top", fill="x", pady=(0, sp(2)))
        tk.Label(head, text="Navbat", font=F["heading"], fg=C["ink"], bg=s100).pack(side="left")
        self.count = tk.Label(head, text="", font=F["caption"], fg=C["ink-secondary"], bg=s100)
        self.count.pack(side="right")
        self.tree = QueueList(body, on_insert=self._probe, on_remove=self.remove_row, on_change=self._count,
                              empty_text="Navbat boʻsh. «Video qoʻshish» bilan video tanlang.")
        self.tree.pack(side="top", fill="both", expand=True)

    def write_log(self, text):
        self.log.append(text)

    def _count(self):
        n = len(self.tree.get_children())
        self.count.config(text=f"{n} ta video" if n else "")

    def _probe(self, iid, path):
        threading.Thread(target=lambda: self.events.put(("meta", iid, describe(path))), daemon=True).start()

    def remove_row(self, iid):
        if not self.worker:
            self.tree.delete(iid)

    def _show_doctor(self, msg):
        title, body = split_doctor(msg)
        body = (body.rstrip(".") + ". " if body else "") + "Muammo hal boʻlmaguncha Boshlash oʻchiq turadi."
        fix = os.path.join(ROOT, "SDK_ornatish.bat")
        if "SDK_ornatish.bat" in msg and os.path.exists(fix):
            self.banner.set(title, body, "SDK_ornatish.bat", lambda: os.startfile(fix))
        else:
            self.banner.set(title, body)
        self.banner.pack(fill="x", padx=sp(6), pady=(sp(4), 0), before=self.toolbar)

    # ---------- ro'yxat ----------
    def add_files(self):
        for p in filedialog.askopenfilenames(title="Videolarni tanlang", filetypes=VIDEO_TYPES):
            p = os.path.normpath(p)
            if p not in [self.tree.set(i, "file") for i in self.tree.get_children()]:
                self.tree.insert("", "end", values=(p, "navbatda"))

    def remove_selected(self):
        if not self.worker:
            for i in self.tree.selection():
                self.tree.delete(i)

    def clear(self):
        if not self.worker:
            self.tree.delete(*self.tree.get_children())

    def pick_out(self):
        d = filedialog.askdirectory(title="Chiqish papkasi")
        if d:
            self.out_dir.set(os.path.normpath(d))

    def open_output(self):
        if self.last_output and os.path.exists(self.last_output):
            subprocess.Popen(["explorer", "/select,", self.last_output])

    # ---------- ishga tushirish ----------
    def out_path(self, inp, preview):
        stem = os.path.splitext(os.path.basename(inp))[0]
        d = self.out_dir.get().strip() or os.path.dirname(inp)
        return os.path.join(d, stem + ("_preview.mp4" if preview else "_eyecontact.mp4"))

    def start(self, preview=False):
        if self.worker:
            return
        items = [i for i in self.tree.get_children() if self.tree.set(i, "status") != "tayyor" or preview]
        if preview:
            items = list(self.tree.selection()[:1]) or items[:1]
        if not items:
            messagebox.showinfo("Eye Contact", "Avval video qoʻshing.")
            return
        d = self.out_dir.get().strip()
        if d and not os.path.isdir(d):
            messagebox.showerror("Eye Contact", f"Chiqish papkasi topilmadi:\n{d}")
            return
        self._save()
        self.stop_flag = False
        self.btn_start.config(state="disabled")
        self.btn_prev.config(state="disabled")
        self.btn_stop.config(state="normal")
        jobs = [(i, self.tree.set(i, "file")) for i in items]
        self.worker = threading.Thread(target=self.run_jobs, args=(jobs, preview, round(self.lid_open.get(), 2),
                                                                   self.hevc.get()), daemon=True)
        self.worker.start()

    def run_jobs(self, jobs, preview, lid_open, hevc):
        for n, (item, inp) in enumerate(jobs, 1):
            if self.stop_flag:
                break
            out = self.out_path(inp, preview)
            cmd = [python_exe(), "-m", "eyecontact.cli", inp, out, "--progress", "--lid-open", str(lid_open)]
            cmd += ["--preview", "30"] if preview else ["--resume"]
            if hevc:
                cmd += ["--codec", "hevc"]
            self.events.put(("begin", item, f"[{n}/{len(jobs)}] {os.path.basename(inp)}"))
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
            if self.sdk_dir:
                env["NVAR_SDK_DIR"] = self.sdk_dir
            try:
                self.proc = subprocess.Popen(cmd, cwd=ROOT, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                             text=True, encoding="utf-8", errors="replace", env=env,
                                             creationflags=NO_WINDOW)
            except OSError as e:
                self.events.put(("end", item, 1, None, str(e)))
                continue
            final, last_err = None, ""
            for line in self.proc.stderr:
                line = line.rstrip()
                if line.startswith("PROGRESS "):
                    _, d, t = line.split()
                    self.events.put(("progress", item, int(d), int(t)))
                elif line.startswith("OUTPUT "):
                    final = line[7:]
                elif line:
                    last_err = line
                    self.events.put(("log", line))
            rc = self.proc.wait()
            self.proc = None
            self.events.put(("end", item, rc, final, last_err))
        self.events.put(("done",))

    def stop(self):
        self.stop_flag = True
        p = self.proc
        if p and p.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=NO_WINDOW)
        self.status.config(text="Toʻxtatildi. «Boshlash» bosilsa uzilgan joydan davom etadi.")

    # ---------- hodisalar (UI thread) ----------
    def pump(self):
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "doctor":
                    _, ok, msg, sdk_dir = ev
                    self.sdk_dir = sdk_dir
                    self.write_log(("Tekshiruv OK: " if ok else "Tekshiruv XATO: ") + msg)
                    if ok:
                        self.btn_start.config(state="normal")
                        self.btn_prev.config(state="normal")
                        self.status.config(text="Tayyor. Video qoʻshing va «Boshlash» ni bosing.")
                    else:
                        self.status.config(text="Dastur ishlay olmaydi, sababi yuqorida.")
                        self._show_doctor(msg)
                elif kind == "meta":
                    self.tree.set_meta(ev[1], ev[2])
                elif kind == "begin":
                    self.t0, self.p0, self.title = time.time(), None, ev[2]
                    self.tree.set(ev[1], "status", "ishlanmoqda…")
                    self.tree.see(ev[1])
                    self.status.config(text=f"{ev[2]}: model yuklanmoqda…")
                    self.write_log("— " + ev[2])
                elif kind == "progress":
                    _, item, d, t = ev
                    now = time.time()
                    if self.p0 is None:
                        self.p0 = (now, d)
                    frac = d / max(t, 1)
                    dt, dd = now - self.p0[0], d - self.p0[1]
                    fps = dd / dt if dt > 2 and dd > 0 else 0
                    stat = f"{fps:.0f} kadr/s · qolgan {fmt_time((t - d) / fps)}" if fps else ""
                    self.tree.set(item, "status", f"ishlanmoqda {frac * 100:.0f}%")
                    self.tree.progress(item, d, t, stat)
                    self.status.config(text=self.title)
                elif kind == "log":
                    self.write_log(ev[1])
                elif kind == "end":
                    _, item, rc, final, err = ev
                    if rc == 0:
                        self.tree.set(item, "status", "tayyor")
                        if final:
                            self.last_output = final
                            self.btn_open.config(state="normal")
                            self.write_log("natija: " + final)
                            if final.lower().endswith("_preview.mp4"):
                                os.startfile(final)
                    elif self.stop_flag:
                        self.tree.set(item, "status", "to'xtatildi")
                    else:
                        self.tree.set_reason(item, err or f"kod {rc}")
                        self.tree.set(item, "status", "xato")
                        self.write_log("XATO: " + (err or f"kod {rc}"))
                elif kind == "done":
                    self.worker = None
                    self.btn_start.config(state="normal")
                    self.btn_prev.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    if not self.stop_flag:
                        self.status.config(text="Tayyor.")
        except queue.Empty:
            pass
        self.root.after(100, self.pump)

    # ---------- sozlamalar ----------
    def _load(self):
        try:
            with open(SETTINGS, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save(self):
        try:
            with open(SETTINGS, "w", encoding="utf-8") as f:
                json.dump({"out_dir": self.out_dir.get(), "lid_open": round(self.lid_open.get(), 2),
                           "hevc": self.hevc.get()}, f)
        except OSError:
            pass

    def on_close(self):
        if self.worker and not messagebox.askyesno(
                "Eye Contact", "Ishlov davom etmoqda. Toʻxtatib chiqilsinmi?\n(Keyin uzilgan joydan davom ettirsa boʻladi.)"):
            return
        self.stop()
        self._save()
        self.root.destroy()


def main():
    dpi_aware()
    root = tk.Tk()
    App(root)                      # App.__init__ -> theme.init(root): dark tema, shriftlar, ttk uslublari
    root.mainloop()


if __name__ == "__main__":
    main()
