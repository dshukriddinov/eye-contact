"""UI ning odamsiz sinovi: oynani ochadi, 10 s klipni navbatga qo'yadi, «Boshlash» ni bosadi, tugashini kutadi,
natija faylini tekshiradi (kadr soni, audio).
    runtime\\python\\python.exe tests\\test_gui.py
"""
import os
import shutil
import sys
import time
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from eyecontact import gui, theme, video_io  # noqa: E402

# theme.py ranglari design-system/tokens.json (dark) bilan bir xil bo'lishi kerak
TOKENS = os.path.join(os.path.dirname(HERE), "design-system", "tokens.json")
if os.path.exists(TOKENS):
    import json
    with open(TOKENS, encoding="utf-8") as f:
        dark = {t["name"]: t["value"]["dark"] for t in json.load(f)["color"]["tokens"]}
    assert theme.COLORS == dark, {k: (theme.COLORS.get(k), v) for k, v in dark.items() if theme.COLORS.get(k) != v}

OUT = os.path.join(HERE, "_gui_out")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
gui.SETTINGS = os.path.join(OUT, "settings.json")   # foydalanuvchi sozlamalariga tegmaslik uchun

gui.dpi_aware()
root = tk.Tk()
app = gui.App(root)
app.out_dir.set(OUT)
app.tree.insert("", "end", values=(os.path.join(HERE, "clip_10s.mp4"), "navbatda"))
t0 = time.time()


def tick():
    if app.worker is None and time.time() - t0 > 2:
        root.after(300, finish)
    elif time.time() - t0 > 300:
        print("TIMEOUT")
        app.stop()
        root.destroy()
        sys.exit(1)
    else:
        root.after(200, tick)


def finish():
    item = app.tree.get_children()[0]
    status = app.tree.set(item, "status")
    row = app.tree.row(item)               # progress endi navbat qatorida (QueueRow + ProgressBar)
    out, badge, frac, done, total = app.last_output, row.badge.text, row.frac, row.done, row.total
    root.destroy()
    assert status == "tayyor", status
    assert badge == "Tayyor", badge        # StatusBadge so'zi
    assert frac == 1.0 and total == 250 and 0 < done <= total, (frac, done, total)   # PROGRESS satrlari o'qilgan
    assert out and os.path.exists(out), out
    m, mi = video_io.probe(out), video_io.probe(os.path.join(HERE, "clip_10s.mp4"))
    assert m["nb_frames"] == mi["nb_frames"], (m["nb_frames"], mi["nb_frames"])
    assert m["audio_codec"] == mi["audio_codec"]
    print(f"OK: UI orqali {m['nb_frames']} kadr, natija {os.path.basename(out)}, audio {m['audio_codec']}")
    shutil.rmtree(OUT, ignore_errors=True)


root.after(500, app.start)
root.after(700, tick)
root.mainloop()
