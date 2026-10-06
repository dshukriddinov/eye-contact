"""Dizayn tizimi komponentlari (design-system/components/*) tkinter'da.

Tk canvas Windows'da yumaloq chiziqlarni silliqlamaydi, shuning uchun yumaloq shakllar (tugma, pill, trek, slayder,
panel) va ikonkalar numpy bilan anti-aliasing'li RGBA qilib chiziladi va PNG orqali PhotoImage bo'ladi.
Matn esa oddiy canvas/Label matni (ClearType).
"""
import base64
import os
import struct
import time
import tkinter as tk
import zlib
from tkinter import ttk

import numpy as np

from . import theme
from .theme import C, F, px, sp

# ---------------------------------------------------------------- rasm yordamchilari

_CACHE = {}


def _rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def _photo(rgba):
    """HxWx4 uint8 -> tk.PhotoImage (PNG, alfa kanal bilan)."""
    h, w = rgba.shape[:2]
    raw = np.concatenate([np.zeros((h, 1), np.uint8), rgba.reshape(h, -1)], axis=1).tobytes()

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b""))
    return tk.PhotoImage(data=base64.b64encode(png).decode("ascii"), format="png")


def _cover(w, h, r, inset=0.0):
    """Yumaloq to'rtburchak qoplamasi 0..1 (signed distance, 1 px anti-aliasing)."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    hw, hh = w / 2 - inset, h / 2 - inset
    r = max(0.0, min(r - inset, hw, hh))
    qx = np.abs(x - w / 2) - (hw - r)
    qy = np.abs(y - h / 2) - (hh - r)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    return np.clip(0.5 - d, 0, 1)


def rrect(w, h, r, fill=None, outline=None, bw=0.0, cache=True):
    """Yumaloq to'rtburchak rasmi: fill (ichki rang), outline + bw (chegara). Ikkalasi ham bo'lishi mumkin."""
    w, h = max(1, int(round(w))), max(1, int(round(h)))
    key = (w, h, round(r, 2), fill, outline, round(bw, 2))
    if cache and key in _CACHE:
        return _CACHE[key]
    outer = _cover(w, h, r)
    if outline and bw:
        inner = _cover(w, h, r, bw)
        if fill:
            a = outer
            rgb = (_rgb(fill) * inner[..., None] + _rgb(outline) * (outer - inner)[..., None]) / np.maximum(a, 1e-6)[..., None]
        else:
            a, rgb = outer - inner, np.broadcast_to(_rgb(outline), (h, w, 3))
    else:
        a, rgb = outer, np.broadcast_to(_rgb(fill), (h, w, 3))
    img = _photo(np.dstack([np.clip(rgb, 0, 255), a * 255]).round().astype(np.uint8))
    if cache:
        _CACHE[key] = img
    return img


# 20 birlikli to'r. Faqat design-system preview.html dagi SVG yo'llari (brand book: yangi belgi o'ylab topilmaydi).
ICONS = {
    "x": [[(5, 5), (15, 15)], [(15, 5), (5, 15)]],                                        # Button/preview.html
    "check": [[(4, 10), (8, 14), (16, 6)]],                                                # Checkbox/preview.html
    "folder": [[(3, 6), (4, 5), (8, 5), (9.5, 7), (16, 7), (17, 8), (17, 14), (16, 15),   # Toolbar/preview.html
                (4, 15), (3, 14), (3, 6)]],
    "warning": [[(10, 2), (1, 17), (19, 17), (10, 2)], [(10, 8), (10, 12)],               # DoctorBanner/preview.html
                [(10, 14.5), (10, 14.51)]],
}


def icon(name, size, color, stroke=1.5):
    """Chiziqli ikonka (currentColor o'rniga `color`), stroke 20 birlikli to'rda."""
    key = ("icon", name, size, color, stroke)
    if key in _CACHE:
        return _CACHE[key]
    s = size / 20.0
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) + 0.5
    d = np.full((size, size), 1e9, np.float32)
    for line in ICONS[name]:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            ax, ay, bx, by = ax * s, ay * s, bx * s, by * s
            vx, vy = bx - ax, by - ay
            t = np.clip(((x - ax) * vx + (y - ay) * vy) / max(vx * vx + vy * vy, 1e-6), 0, 1)
            d = np.minimum(d, np.hypot(x - (ax + t * vx), y - (ay + t * vy)))
    a = np.clip(stroke * s / 2 + 0.5 - d, 0, 1)
    rgb = np.broadcast_to(_rgb(color), (size, size, 3))
    img = _CACHE[key] = _photo(np.dstack([rgb, a * 255]).round().astype(np.uint8))
    return img


def _canvas(parent, bg, **kw):
    return tk.Canvas(parent, bg=bg, highlightthickness=0, bd=0, **kw)


# ---------------------------------------------------------------- Panel

class Panel(tk.Canvas):
    """Yumaloq panel: fill + 1 px hairline + radius. Bolalar `.body` ichiga, `pad` ichkarida.
    fit=True: balandlik tarkibga moslanadi (settings strip, banner); aks holda pack/expand beradi."""

    def __init__(self, parent, fill="surface-200", border="border", radius="lg", pad=0, fit=False, bg=None):
        super().__init__(parent, bg=bg or theme.widget_bg(parent), highlightthickness=0, bd=0)
        self.fill, self.border = C[fill], (C[border] if border else None)
        self.padx, self.pady = pad if isinstance(pad, tuple) else (pad, pad)
        self.r, self.fit = px(theme.RADIUS[radius]), fit
        self.body = tk.Frame(self, bg=self.fill)
        self.win = self.create_window(self.padx, self.pady, window=self.body, anchor="nw")
        self.bind("<Configure>", self._layout)
        if fit:
            self.body.bind("<Configure>", self._fit, add="+")

    def _layout(self, e):
        self.delete("bg")
        self._img = rrect(e.width, e.height, self.r, self.fill, self.border, theme.k if self.border else 0, cache=False)
        self.create_image(0, 0, anchor="nw", image=self._img, tags="bg")
        size = {"width": max(1, e.width - 2 * self.padx)}
        if not self.fit:
            size["height"] = max(1, e.height - 2 * self.pady)
        self.itemconfigure(self.win, **size)

    def _fit(self, _e=None):
        h = self.body.winfo_reqheight() + 2 * self.pady
        if int(float(str(self.cget("height")))) != h:
            tk.Canvas.configure(self, height=h)


def _autohide(sb, first, last):
    first, last = float(first), float(last)
    if first <= 0.0 and last >= 1.0:
        sb.pack_forget()
    elif not sb.winfo_ismapped():
        sb.pack(side="right", fill="y")
    sb.set(first, last)


# ---------------------------------------------------------------- Button

class Button(tk.Canvas):
    """Button: primary (Boshlash), secondary, ghost, icon. States: rest, hover, pressed, focus (focus-ring), disabled.
    ring=False: focus halqasi va Tab tartibi yo'q (qator ichidagi olib tashlash tugmasi)."""

    def __init__(self, parent, text="", variant="secondary", command=None, icon_name=None, state="normal", bg=None,
                 ring=True):
        self.bgc = bg or theme.widget_bg(parent)
        self.text, self.variant, self.command, self.icon_name = text, variant, command, icon_name
        self._st, self.hover, self.pressed, self.focused, self.visible = state, False, False, False, True
        self.ring = ring
        self.m = px(theme.RING) if ring else 0
        super().__init__(parent, bg=self.bgc, highlightthickness=0, bd=0, takefocus=0)
        self._measure()
        for ev, fn in (("<Enter>", self._enter), ("<Leave>", self._leave), ("<ButtonPress-1>", self._press),
                       ("<ButtonRelease-1>", self._release), ("<FocusIn>", self._focus_in),
                       ("<FocusOut>", self._focus_out), ("<Key-space>", self._key), ("<Return>", self._key)):
            self.bind(ev, fn)
        self._draw()

    def _measure(self):
        if self.variant == "icon":
            self.bw = self.bh = px(theme.MIN_TARGET)
        else:
            padx = sp(2) if self.variant == "ghost" else sp(3)
            self.bw = F["body"].measure(self.text) + 2 * padx
            self.bh = max(px(theme.MIN_TARGET), F["body"].metrics("linespace") + 2 * sp(2))
        on = self._st != "disabled" and self.ring
        tk.Canvas.configure(self, width=self.bw + 2 * self.m, height=self.bh + 2 * self.m, takefocus=1 if on else 0)

    def configure(self, cnf=None, **kw):
        state, text = kw.pop("state", None), kw.pop("text", None)
        if cnf or kw or (state is None and text is None):
            return tk.Canvas.configure(self, cnf, **kw)
        if text is not None and text != self.text:
            self.text = text
        if state is not None:
            self._st = state
            if state == "disabled":
                self.pressed = False
        self._measure()
        self._draw()

    config = configure

    def set_bg(self, bg):
        self.bgc = bg
        tk.Canvas.configure(self, bg=bg)
        self._draw()

    def set_visible(self, on):
        if on != self.visible:
            self.visible = on
            self._draw()

    def _colors(self):
        v, hot = self.variant, self._st != "disabled" and (self.hover or self.pressed)
        if self._st == "disabled":
            return (None if v == "ghost" else C["surface-400"]), None, C["ink-tertiary"]
        if v == "primary":
            fill, outline, txt = (C["accent-strong"] if hot else C["accent"]), None, C["on-accent"]
        elif v == "ghost":
            fill, outline, txt = (C["surface-300"] if hot else None), None, (C["ink"] if hot else C["ink-secondary"])
        else:  # secondary, icon
            fill, outline = (C["surface-300"] if hot else C["surface-200"]), C["border-strong"]
            txt = C["ink"] if (v == "secondary" or hot) else C["ink-secondary"]
        if self.pressed and fill:
            fill = theme.mix(fill, self.bgc, 0.15)   # bosilgan: hover rangi, biroz pastroq shaffoflik
        return fill, outline, txt

    def _draw(self):
        self.delete("all")
        if not self.visible:
            return
        fill, outline, txt = self._colors()
        m, w, h, r = self.m, self.bw, self.bh, px(theme.RADIUS["md"])
        if fill or outline:
            self.create_image(m, m, anchor="nw", image=rrect(w, h, r, fill, outline, theme.k if outline else 0))
        if self.focused:
            self.create_image(0, 0, anchor="nw", image=rrect(w + 2 * m, h + 2 * m, r + m, None, C["accent-strong"],
                                                              2 * theme.k))
        if self.variant == "icon":
            self.create_image(m + w / 2, m + h / 2, image=icon(self.icon_name or "x", px(16), txt))
        else:
            self.create_text(m + w / 2, m + h / 2, text=self.text, fill=txt, font=F["body"])

    def _enter(self, _e):
        self.hover = True
        self._draw()

    def _leave(self, _e):
        self.hover = self.pressed = False
        self._draw()

    def _press(self, _e):
        if self._st != "disabled" and self.visible:
            self.pressed = True
            self._draw()

    def _release(self, e):
        fire = self.pressed and 0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height()
        self.pressed = False
        self._draw()
        if fire:
            self.invoke()

    def _focus_in(self, _e):
        self.focused = True
        self._draw()

    def _focus_out(self, _e):
        self.focused = False
        self._draw()

    def _key(self, _e):
        self.invoke()

    def invoke(self):
        if self._st != "disabled" and self.visible and self.command:
            self.command()


# ---------------------------------------------------------------- StatusBadge, ProgressBar

KINDS = {"queued": ("muted", "muted-subtle"), "processing": ("accent", "accent-subtle"),
         "done": ("success", "success-subtle"), "stopped": ("muted", "muted-subtle"),
         "error": ("danger", "danger-subtle")}

# gui.py dagi ichki holat satrlari -> (tur, ko'rinadigan so'z)
STATUS_WORDS = {"navbatda": ("queued", "Navbatda"), "tayyor": ("done", "Tayyor"),
                "to'xtatildi": ("stopped", "Toʻxtatildi"), "xato": ("error", "Xato")}


def status_view(s):
    if s.startswith("ishlanmoqda"):
        return "processing", "Ishlanmoqda" + s[len("ishlanmoqda"):]
    return STATUS_WORDS.get(s, ("queued", s.capitalize()))


class StatusBadge(tk.Canvas):
    """StatusBadge: rang + so'z birga. label shrift, space-1 / space-2 ichki bo'shliq, radius-full, rangli nuqta."""

    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=bg or theme.widget_bg(parent), highlightthickness=0, bd=0, width=1, height=1)
        self.kind = self.text = None

    def set(self, kind, text):
        if (kind, text) == (self.kind, self.text):
            return
        self.kind, self.text = kind, text
        fg, tint = (C[t] for t in KINDS[kind])
        f, dot, gap, padx, pady = F["label"], px(6), sp(1), sp(2), sp(1)
        w = padx + dot + gap + f.measure(text) + padx
        h = f.metrics("linespace") + 2 * pady
        tk.Canvas.configure(self, width=w, height=h)
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=rrect(w, h, h / 2, tint))
        self.create_image(padx + dot / 2, h / 2, image=rrect(dot, dot, dot / 2, fg))
        self.create_text(padx + dot + gap, h / 2, text=text, anchor="w", fill=fg, font=f)


BAR = {"processing": "accent", "stopped": "muted", "error": "danger"}


class ProgressBar(tk.Canvas):
    """ProgressBar: 6 px, surface-400 trek, radius-full. Fill rangi holatga ergashadi, kengligi 180 ms ease-out."""

    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=bg or theme.widget_bg(parent), highlightthickness=0, bd=0, width=1, height=px(6))
        self.frac = self.shown = 0.0
        self.kind, self._anim, self._imgs = "processing", None, []
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, frac, kind="processing"):
        self.frac, self.kind = max(0.0, min(1.0, frac)), kind
        if self._anim:
            self.after_cancel(self._anim)
            self._anim = None
        if not self.winfo_ismapped():
            self.shown = self.frac
            return
        start, t0 = self.shown, time.perf_counter()

        def step():
            t = min(1.0, (time.perf_counter() - t0) / 0.18)
            self.shown = start + (self.frac - start) * (1 - (1 - t) ** 3)
            self._draw()
            self._anim = self.after(16, step) if t < 1 else None
        step()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), px(6)
        if w < 2:
            return
        self._imgs = [rrect(w, h, h / 2, C["surface-400"])]
        self.create_image(0, 0, anchor="nw", image=self._imgs[0])
        fw = round(self.shown * w)
        if fw > 0:
            self._imgs.append(rrect(max(fw, h), h, h / 2, C[BAR[self.kind]], cache=False))
            self.create_image(0, 0, anchor="nw", image=self._imgs[1])


# ---------------------------------------------------------------- Slider, Checkbox

class Slider(tk.Frame):
    """Slider: label tepada, qiymat stat shriftda (accent) o'ngda, ikki uchida caption. Trek 4 px surface-400,
    to'ldirilgan qism accent, thumb 16 px accent + 2 px surface-100 halqa. Strelkalar 0.01 qadam."""

    MARGIN = 8 + theme.RING      # thumb radiusi + focus-ring: trek chetidan tashqariga chiqadigan qism, CSS px

    def __init__(self, parent, variable, label, left, right, bg=None):
        bg = bg or theme.widget_bg(parent)
        super().__init__(parent, bg=bg)
        self.var, self.focused, self._imgs = variable, False, []
        m = px(self.MARGIN)
        head = tk.Frame(self, bg=bg)
        head.pack(fill="x", padx=m)
        tk.Label(head, text=label, font=F["label"], fg=C["ink-secondary"], bg=bg).pack(side="left")
        self.val = tk.Label(head, font=F["stat"], fg=C["accent"], bg=bg)
        self.val.pack(side="right")
        self.cv = _canvas(self, bg, width=1, height=px(24), takefocus=1)
        self.cv.pack(fill="x")
        ends = tk.Frame(self, bg=bg)
        ends.pack(fill="x", padx=m)
        for text, side in ((left, "left"), (right, "right")):
            tk.Label(ends, text=text, font=F["caption"], fg=C["ink-tertiary"], bg=bg).pack(side=side)
        self.cv.bind("<Configure>", lambda e: self._draw())
        self.cv.bind("<ButtonPress-1>", self._drag)
        self.cv.bind("<B1-Motion>", self._drag)
        for key, d in (("<Left>", -0.01), ("<Down>", -0.01), ("<Right>", 0.01), ("<Up>", 0.01)):
            self.cv.bind(key, lambda e, d=d: self._set(self.var.get() + d))
        self.cv.bind("<FocusIn>", lambda e: self._focus(True))
        self.cv.bind("<FocusOut>", lambda e: self._focus(False))
        variable.trace_add("write", lambda *a: self._draw())

    def _span(self):
        m = px(self.MARGIN)
        return m, max(m + 1, self.cv.winfo_width() - m)

    def _drag(self, e):
        x0, x1 = self._span()
        self._set((e.x - x0) / (x1 - x0))

    def _set(self, v):
        self.var.set(round(max(0.0, min(1.0, v)), 2))

    def _focus(self, on):
        self.focused = on
        self._draw()

    def _draw(self):
        try:
            v = float(self.var.get())
        except (tk.TclError, ValueError):
            return
        self.val.config(text=f"{v:.2f}")
        cv = self.cv
        cv.delete("all")
        if cv.winfo_width() < 20:
            return
        x0, x1 = self._span()
        cy, th, x = px(12), px(4), x0 + v * (x1 - x0)
        self._imgs = [rrect(x1 - x0, th, th / 2, C["surface-400"]),
                      rrect(max(th, x - x0), th, th / 2, C["accent"], cache=False)]
        cv.create_image(x0, cy - th / 2, anchor="nw", image=self._imgs[0])
        cv.create_image(x0, cy - th / 2, anchor="nw", image=self._imgs[1])
        cv.create_image(x, cy, image=rrect(px(20), px(20), px(10), C["surface-100"]))
        cv.create_image(x, cy, image=rrect(px(16), px(16), px(8), C["accent"]))
        if self.focused:
            cv.create_image(x, cy, image=rrect(px(24), px(24), px(12), None, C["accent-strong"], 2 * theme.k))


class Checkbox(tk.Frame):
    """Checkbox: 16 px, radius-sm, border-strong chegara, surface-200 fill; belgilanganda accent fill + on-accent
    belgisi. Butun qator (quti + yozuv) bosiladi, Space almashtiradi, focus-ring faqat qutida."""

    def __init__(self, parent, variable, text, caption=None, bg=None):
        bg = bg or theme.widget_bg(parent)
        super().__init__(parent, bg=bg)
        self.var, self.focused = variable, False
        m = px(theme.RING)
        s = px(16) + 2 * m
        self.cv = _canvas(self, bg, width=s, height=s, takefocus=1)
        self.cv.grid(row=0, column=0, padx=(0, max(0, sp(2) - m)))
        lbl = tk.Label(self, text=text, font=F["body"], fg=C["ink"], bg=bg)
        lbl.grid(row=0, column=1, sticky="w")
        clickable = [self.cv, lbl]
        if caption:
            cap = tk.Label(self, text=caption, font=F["caption"], fg=C["ink-secondary"], bg=bg, justify="left")
            cap.grid(row=1, column=1, sticky="w")
            clickable.append(cap)
        for w in clickable:
            w.bind("<Button-1>", self.toggle)
        self.cv.bind("<Key-space>", self.toggle)
        self.cv.bind("<FocusIn>", lambda e: self._focus(True))
        self.cv.bind("<FocusOut>", lambda e: self._focus(False))
        variable.trace_add("write", lambda *a: self._draw())
        self._draw()

    def toggle(self, _e=None):
        self.var.set(not self.var.get())

    def _focus(self, on):
        self.focused = on
        self._draw()

    def _draw(self):
        cv, m, b, r = self.cv, px(theme.RING), px(16), px(theme.RADIUS["sm"])
        cv.delete("all")
        if self.var.get():
            cv.create_image(m, m, anchor="nw", image=rrect(b, b, r, C["accent"]))
            cv.create_image(m + b / 2, m + b / 2, image=icon("check", px(11), C["on-accent"], stroke=2.5))
        else:
            cv.create_image(m, m, anchor="nw", image=rrect(b, b, r, C["surface-200"], C["border-strong"], 1.5 * theme.k))
        if self.focused:
            cv.create_image(0, 0, anchor="nw", image=rrect(b + 2 * m, b + 2 * m, r + m, None, C["accent-strong"],
                                                            2 * theme.k))


# ---------------------------------------------------------------- Toolbar: PathField

class PathField(tk.Canvas):
    """Toolbar chiqish papkasi maydoni: surface-300 fill, radius-md, oldida folder ikonka, bo'sh bo'lsa
    ink-tertiary placeholder. Uzun yo'l chapdan qisqaradi (papka nomi ko'rinib turadi). Qo'lda yozish ham mumkin."""

    def __init__(self, parent, variable, placeholder, min_width=220, bg=None):
        self.bgc = bg or theme.widget_bg(parent)
        super().__init__(parent, bg=self.bgc, highlightthickness=0, bd=0)
        self.var, self.focused, self._img, self.placeholder = variable, False, None, placeholder
        self.m = m = px(theme.RING)
        self.fh = max(px(theme.MIN_TARGET), F["body"].metrics("linespace") + 2 * sp(2))
        tk.Canvas.configure(self, height=self.fh + 2 * m, width=px(min_width) + 2 * m)
        fill = C["surface-300"]
        self.entry = tk.Entry(self, textvariable=variable, font=F["body"], fg=C["ink"], bg=fill, relief="flat", bd=0,
                              highlightthickness=0, insertbackground=C["ink"], selectbackground=C["accent-subtle"],
                              selectforeground=C["ink"])
        self.ph = tk.Label(self, text=placeholder, font=F["body"], fg=C["ink-tertiary"], bg=fill, anchor="w",
                           cursor="xterm")
        self.ph.bind("<Button-1>", lambda e: self.entry.focus_set())
        self.entry.bind("<FocusIn>", lambda e: self._focus(True))
        self.entry.bind("<FocusOut>", lambda e: self._focus(False))
        self.bind("<Configure>", lambda e: self._draw())
        variable.trace_add("write", lambda *a: self.after_idle(self._sync))

    def _focus(self, on):
        self.focused = on
        self._draw()

    def _draw(self):
        w, m, fh, r = self.winfo_width(), self.m, self.fh, px(theme.RADIUS["md"])
        if w < 4 * m:
            return
        self.delete("all")
        self._img = rrect(w - 2 * m, fh, r, C["surface-300"], cache=False)
        self.create_image(m, m, anchor="nw", image=self._img)
        self.create_image(m + sp(3) + px(8), m + fh / 2, image=icon("folder", px(16), C["ink-secondary"]))
        if self.focused:
            self._ring = rrect(w, fh + 2 * m, r + m, None, C["accent-strong"], 2 * theme.k, cache=False)
            self.create_image(0, 0, anchor="nw", image=self._ring)
        x = m + sp(3) + px(16) + sp(2)
        eh = self.entry.winfo_reqheight()
        geo = dict(x=x, y=m + (fh - eh) / 2, width=max(10, w - m - sp(3) - x), height=eh)
        self.entry.place(**geo)
        self._geo = geo
        self._sync()

    def _sync(self):
        if not hasattr(self, "_geo"):
            return
        self.entry.xview_moveto(1.0)
        if self.focused:
            self.ph.place_forget()
            return
        v = self.var.get()
        self.ph.config(text=self._elide(v) if v else self.placeholder, fg=C["ink"] if v else C["ink-tertiary"])
        self.ph.place(**self._geo)

    def _elide(self, s):
        f, room = F["body"], self._geo["width"] - px(6)      # Label ichki chegarasi uchun zaxira
        if f.measure(s) <= room:
            return s
        for i in range(1, len(s)):
            if f.measure("…" + s[i:]) <= room:
                return "…" + s[i:]
        return "…"


# ---------------------------------------------------------------- QueueRow, QueueList

def _n(v):
    return f"{v:,}".replace(",", " ")


class QueueRow(tk.Frame):
    """QueueRow: fayl nomi body-strong, ostida caption (o'lcham · davomiylik · hajm), o'ng tepada StatusBadge,
    faqat ishlanmoqda / to'xtatildi holatida ProgressBar. Fill holatdan qat'i nazar surface-200, hover/tanlanganda
    surface-300. Olib tashlash (icon) tugmasi faqat hover'da ko'rinadi."""

    def __init__(self, parent, path, status, on_remove, on_click):
        bg = C["surface-200"]
        super().__init__(parent, bg=bg)
        self.path, self.status, self.iid = path, status, None
        self.selected = self.hover = False
        self.done = self.total = 0
        self.frac, self.reason = 0.0, ""
        self.divider = tk.Frame(self, bg=C["border"], height=max(1, round(theme.k)))
        self.box = tk.Frame(self, bg=bg)
        self.box.pack(fill="x", padx=sp(3), pady=sp(3))
        top = tk.Frame(self.box, bg=bg)
        top.pack(fill="x")
        self.rm = Button(top, variant="icon", icon_name="x", command=lambda: on_remove(self), bg=bg, ring=False)
        self.rm.pack(side="right", anchor="n", padx=(sp(2), 0))
        self.rm.set_visible(False)
        self.badge = StatusBadge(top, bg=bg)
        self.badge.pack(side="right", anchor="n")
        left = tk.Frame(top, bg=bg)
        left.pack(side="left", fill="x", expand=True)
        self.name = tk.Label(left, text=os.path.basename(path), font=F["body-strong"], fg=C["ink"], bg=bg, anchor="w")
        self.name.pack(fill="x")
        self.meta = tk.Label(left, text="", font=F["caption"], fg=C["ink-secondary"], bg=bg, anchor="w")
        self.meta.pack(fill="x", pady=(px(2), 0))
        self.err = tk.Label(self.box, font=F["caption"], fg=C["danger"], bg=bg, anchor="w", justify="left")
        self.bar = tk.Frame(self.box, bg=bg)
        stats = tk.Frame(self.bar, bg=bg)
        stats.pack(fill="x", pady=(0, sp(1)))
        self.left_s = tk.Label(stats, font=F["caption"], fg=C["ink-secondary"], bg=bg)
        self.left_s.pack(side="left")
        self.right_s = tk.Label(stats, font=F["stat"], fg=C["ink-secondary"], bg=bg)
        self.right_s.pack(side="right")
        self.pb = ProgressBar(self.bar, bg=bg)
        self.pb.pack(fill="x")
        self._bgw = [self, self.box, top, left, self.name, self.meta, self.err, self.bar, stats, self.left_s,
                     self.right_s, self.badge, self.pb]
        for w in self._bgw + [self.rm]:
            w.bind("<Enter>", lambda e: self._set_hover(True), add="+")
            w.bind("<Leave>", lambda e: self.after_idle(self._check_hover), add="+")
        for w in self._bgw:
            w.bind("<Button-1>", lambda e: on_click(self, e), add="+")
        self.set_status(status)

    def set_status(self, s):
        self.status = s
        kind, word = status_view(s)
        self.badge.set(kind, word)
        if kind == "done":
            self.frac = 1.0
        if kind in ("processing", "stopped"):
            if kind == "stopped":
                self.right_s.config(text="toʻxtatildi")
            elif s.endswith("…"):
                self.right_s.config(text="")
                if not self.total:
                    self.left_s.config(text="Model yuklanmoqda…")
            self.pb.set(self.frac, kind)
            if not self.bar.winfo_manager():
                self.bar.pack(fill="x", pady=(sp(2), 0))
        else:
            self.bar.pack_forget()
        if kind == "error" and self.reason:
            self.err.config(text=self.reason)
            self.err.pack(fill="x", pady=(sp(1), 0))
        else:
            self.err.pack_forget()

    def progress(self, done, total, stat=""):
        self.done, self.total = done, total
        self.frac = done / max(total, 1)
        self.left_s.config(text=f"{_n(done)} / {_n(total)} kadr")
        self.right_s.config(text=stat)
        self.pb.set(self.frac, "processing")

    def set_meta(self, text):
        self.meta.config(text=text)

    def set_reason(self, text):
        self.reason = text

    def _check_hover(self):
        if not self.winfo_exists():
            return
        try:
            w = self.winfo_containing(*self.winfo_pointerxy())
        except (KeyError, tk.TclError):
            w = None
        while w is not None and w is not self:
            w = w.master
        self._set_hover(w is self)

    def _set_hover(self, on):
        if on != self.hover:
            self.hover = on
            self.rm.set_visible(on)
            self.paint()

    def paint(self):
        bg = C["surface-300"] if (self.hover or self.selected) else C["surface-200"]
        for w in self._bgw:
            w.configure(bg=bg)
        self.rm.set_bg(bg)


class QueueList(Panel):
    """Navbat ro'yxati: QueueRow'lar, 1 px border chiziq qatorlar orasida, radius-md faqat ro'yxat burchaklarida.
    ttk.Treeview'ning gui.py ishlatadigan qismini takrorlaydi (insert, get_children, set, selection, delete, see),
    shuning uchun navbat mantig'i o'zgarmagan."""

    def __init__(self, parent, on_insert=None, on_remove=None, on_change=None, empty_text="", bg=None):
        super().__init__(parent, fill="surface-200", border="border", radius="md", pad=px(3), bg=bg)
        self.on_insert, self.on_remove, self.on_change = on_insert, on_remove, on_change
        self.rows, self.order, self._n = {}, [], 0
        fill = C["surface-200"]
        self.cv = _canvas(self.body, fill, width=1, height=1, yscrollincrement=px(20))
        self.sb = ttk.Scrollbar(self.body, orient="vertical", style="EC.Vertical.TScrollbar", command=self.cv.yview)
        self.cv.configure(yscrollcommand=lambda a, b: _autohide(self.sb, a, b))
        self.cv.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.cv, bg=fill)
        self.iwin = self.cv.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=(0, 0, e.width, e.height)))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.iwin, width=e.width))
        self.empty = tk.Label(self.cv, text=empty_text, font=F["body"], fg=C["ink-secondary"], bg=fill)
        self.bind_all("<MouseWheel>", self._wheel, add="+")
        self._refresh(notify=False)

    # --- Treeview bilan mos API
    def insert(self, _parent, _index, values):
        path, status = values[0], values[1]
        self._n += 1
        iid = f"I{self._n:03d}"
        row = QueueRow(self.inner, path, status, on_remove=self._remove, on_click=self._click)
        row.iid = iid
        self.rows[iid] = row
        self.order.append(iid)
        row.pack(fill="x")
        self._refresh()
        if self.on_insert:
            self.on_insert(iid, path)
        return iid

    def get_children(self, _item=None):
        return tuple(self.order)

    def set(self, iid, column, value=None):
        row = self.rows[iid]
        if value is None:
            return row.path if column == "file" else row.status
        if column == "status":
            row.set_status(value)

    def selection(self):
        return tuple(i for i in self.order if self.rows[i].selected)

    def delete(self, *iids):
        for i in iids:
            row = self.rows.pop(i, None)
            if row:
                self.order.remove(i)
                row.destroy()
        self._refresh()

    def see(self, iid):
        row = self.rows.get(iid)
        if not row:
            return
        self.update_idletasks()
        total, view = max(1, self.inner.winfo_height()), self.cv.winfo_height()
        top, y, h = self.cv.canvasy(0), row.winfo_y(), row.winfo_height()
        if y < top or y + h > top + view:
            self.cv.yview_moveto(y / total)

    # --- qo'shimcha
    def row(self, iid):
        return self.rows[iid]

    def progress(self, iid, done, total, stat=""):
        if iid in self.rows:
            self.rows[iid].progress(done, total, stat)

    def set_meta(self, iid, text):
        if iid in self.rows:
            self.rows[iid].set_meta(text)

    def set_reason(self, iid, text):
        if iid in self.rows:
            self.rows[iid].set_reason(text)

    def _remove(self, row):
        if self.on_remove:                # o'z tugmasi hodisasi tugagach o'chiriladi
            self.after_idle(self.on_remove, row.iid)

    def _click(self, row, e):
        if e.state & 0x0004:            # Ctrl: qo'shib/ayirib tanlash
            row.selected = not row.selected
        else:
            for r in self.rows.values():
                r.selected = r is row
        for r in self.rows.values():
            r.paint()

    def _refresh(self, notify=True):
        for idx, iid in enumerate(self.order):
            d = self.rows[iid].divider
            if idx and not d.winfo_manager():
                d.pack(fill="x", before=self.rows[iid].box)
            elif not idx and d.winfo_manager():
                d.pack_forget()
        if self.order:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        if notify and self.on_change:
            self.on_change()

    def _wheel(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        while w is not None and w is not self:
            w = w.master
        if w is self and self.sb.winfo_ismapped():
            self.cv.yview_scroll(int(-e.delta / 120), "units")


# ---------------------------------------------------------------- LogPanel

def is_error(msg):
    m = msg.lstrip()
    return m.startswith(("XATO", "Tekshiruv XATO")) or m.lower().startswith("xato:")


LOGFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "gui.log")


def write_logfile(text):
    """Jurnal satrini diskka ham yozadi: xato chiqsa to'liq matn keyin ham qoladi. 2 MB dan oshsa yangidan boshlanadi."""
    try:
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        mode = "w" if os.path.exists(LOGFILE) and os.path.getsize(LOGFILE) > 2_000_000 else "a"
        with open(LOGFILE, mode, encoding="utf-8") as f:
            print(time.strftime("%Y-%m-%d %H:%M:%S ") + text, file=f)
    except OSError:
        pass


class LogPanel(Panel):
    """LogPanel (Jurnal): heading sarlavha, surface-200, radius-lg, border. Qatorlar code (mono): [SS:DD:SS]
    ink-tertiary, xabar ink-secondary, XATO qatori to'liq danger. Qatorlar o'ralmaydi, uzuni "…" bilan qisqaradi,
    to'liq matn hover'da tooltip, bosilsa nusxalanadi. Pastda bo'lsa avtomatik pastga suriladi."""

    def __init__(self, parent, title="Jurnal", lines=5, bg=None):
        super().__init__(parent, fill="surface-200", border="border", radius="lg", pad=sp(3), fit=True, bg=bg)
        fill = C["surface-200"]
        tk.Label(self.body, text=title, font=F["heading"], fg=C["ink"], bg=fill, anchor="w").pack(fill="x",
                                                                                                pady=(0, sp(2)))
        box = tk.Frame(self.body, bg=fill)
        box.pack(fill="both", expand=True)
        self.text = tk.Text(box, width=10, height=lines, font=F["code"], bg=fill, fg=C["ink-secondary"], relief="flat", bd=0,
                            highlightthickness=0, wrap="none", cursor="arrow", spacing1=px(2), spacing3=px(2),
                            insertwidth=0, selectbackground=C["surface-400"], selectforeground=C["ink"], takefocus=0)
        self.sb = ttk.Scrollbar(box, orient="vertical", style="EC.Vertical.TScrollbar", command=self.text.yview)
        self.text.configure(yscrollcommand=lambda a, b: _autohide(self.sb, a, b), state="disabled")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure("ts", foreground=C["ink-tertiary"])
        self.text.tag_configure("err", foreground=C["danger"])
        self.lines, self.cut = [], []      # (vaqt, xabar, xato) va qisqartirilganmi
        self._job, self._tip, self._tip_line, self._width = None, None, None, 0
        self.text.bind("<Configure>", self._resized)
        self.text.bind("<Motion>", self._motion)
        self.text.bind("<Leave>", lambda e: self._tip_hide())
        self.text.bind("<Button-1>", self._copy)

    def append(self, msg):
        ts, err = time.strftime("[%H:%M:%S]"), is_error(msg)
        at_end = self.text.yview()[1] >= 0.999
        for part in msg.rstrip().splitlines() or [""]:
            self.lines.append((ts, part, err))
            self._insert(len(self.lines) - 1)
            write_logfile(part)
        if at_end:
            self.text.see("end")

    def _fit_text(self, msg, ts):
        cw = max(1, F["code"].measure("0"))
        room = (self.text.winfo_width() - 2 * px(4)) // cw - len(ts) - 1
        if room < 8 or len(msg) <= room:
            return msg
        return msg[:room - 1] + "…"

    def _insert(self, i):
        ts, msg, err = self.lines[i]
        shown = self._fit_text(msg, ts)
        if i < len(self.cut):
            self.cut[i] = shown != msg
        else:
            self.cut.append(shown != msg)
        t = self.text
        t.configure(state="normal")
        if i:
            t.insert("end", "\n")
        t.insert("end", ts + " ", ("err",) if err else ("ts",))
        t.insert("end", shown, ("err",) if err else ())
        t.configure(state="disabled")

    def _resized(self, e):
        if e.width != self._width:
            self._width = e.width
            if self._job:
                self.after_cancel(self._job)
            self._job = self.after(80, self._render)

    def _render(self):
        self._job = None
        at_end = self.text.yview()[1] >= 0.999
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        for i in range(len(self.lines)):
            self._insert(i)
        if at_end:
            self.text.see("end")

    def _line_at(self, e):
        i = int(self.text.index(f"@{e.x},{e.y}").split(".")[0]) - 1
        return i if 0 <= i < len(self.lines) else None

    def _motion(self, e):
        i = self._line_at(e)
        if i is None or not self.cut[i]:
            self._tip_hide()
            return
        if i != self._tip_line:
            self._tip_hide()
            ts, msg, err = self.lines[i]
            tip = self._tip = tk.Toplevel(self)
            tip.overrideredirect(True)
            tip.configure(bg=C["border-strong"])
            tk.Label(tip, text=f"{ts} {msg}", font=F["code"], bg=C["surface-300"], fg=C["danger"] if err else C["ink"],
                     padx=sp(2), pady=sp(1), wraplength=px(640), justify="left").pack(padx=1, pady=1)
            self._tip_line = i
        self._tip.geometry(f"+{e.x_root + px(12)}+{e.y_root + px(16)}")

    def _tip_hide(self):
        if self._tip:
            self._tip.destroy()
        self._tip, self._tip_line = None, None

    def _copy(self, e):
        i = self._line_at(e)
        if i is not None:
            ts, msg, _ = self.lines[i]
            self.clipboard_clear()
            self.clipboard_append(f"{ts} {msg}")


# ---------------------------------------------------------------- DoctorBanner

def split_doctor(msg):
    """doctor() xabari -> (sarlavha, matn). Sarlavha: birinchi gap (<= 60 belgi) yoki ':' gacha qism."""
    first, _, rest = msg.partition("\n")
    head, sep, tail = first.partition(". ")
    if len(head) > 60:
        head, sep, tail = first.partition(": ")
    body = " ".join(s.strip() for s in (tail, rest) if s.strip())
    return head.rstrip("."), body


class DoctorBanner(Panel):
    """DoctorBanner (error tonida): danger-subtle fill, danger ikonka va sarlavha, ink matn, radius-md, space-3.
    Faqat doctor() muammo topganda ko'rsatiladi. Tuzatish amali bo'lsa o'ngda ghost Button."""

    def __init__(self, parent, bg=None):
        super().__init__(parent, fill="danger-subtle", border=None, radius="md", pad=sp(3), fit=True, bg=bg)
        b, fill = self.body, C["danger-subtle"]
        ic = _canvas(b, fill, width=px(20), height=px(20))
        ic.create_image(px(10), px(10), image=icon("warning", px(20), C["danger"]))
        ic.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, sp(2)), pady=(px(1), 0))
        self.title = tk.Label(b, font=F["body-strong"], fg=C["danger"], bg=fill, anchor="w", justify="left")
        self.title.grid(row=0, column=1, sticky="ew")
        self.msg = tk.Label(b, font=F["body"], fg=C["ink"], bg=fill, anchor="w", justify="left")
        self.msg.grid(row=1, column=1, sticky="ew")
        self.fix = Button(b, variant="ghost", bg=fill)
        b.columnconfigure(1, weight=1)
        b.bind("<Configure>", self._wrap, add="+")

    def set(self, title, body, fix_text=None, fix_cmd=None):
        self.title.config(text=title)
        self.msg.config(text=body)
        if fix_text:
            self.fix.configure(text=fix_text)
            self.fix.command = fix_cmd
            self.fix.grid(row=0, column=2, rowspan=2, sticky="e", padx=(sp(2), 0))
        else:
            self.fix.grid_forget()

    def _wrap(self, e):
        room = e.width - px(20) - sp(2) - (self.fix.winfo_reqwidth() + sp(2) if self.fix.winfo_manager() else 0)
        for lbl in (self.title, self.msg):
            if int(float(str(lbl.cget("wraplength") or 0))) != max(1, room):
                lbl.configure(wraplength=max(1, room))
