"""Eye Contact dizayn tizimi tokenlari (tkinter uchun). Manba: design-system/tokens.json, dark tema (themes[0]).

Ranglar, shriftlar, bo'shliq va radius bir joyda. O'lchamlar CSS px da, ekranga `px()` bilan o'tkaziladi
(DPI masshtabi `k`, 150% ekranda 1.5). Tokenlar tokens.json bilan mosligi tests/test_gui.py da tekshiriladi.
"""
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# color.tokens, dark
COLORS = {
    "surface-100": "#15141a",
    "surface-200": "#1c1b22",
    "surface-300": "#242329",
    "surface-400": "#2c2b33",
    "border": "#34333c",
    "border-strong": "#46454f",
    "ink": "#f1eee9",
    "ink-secondary": "#b0acb8",
    "ink-tertiary": "#8d8996",
    "accent": "#e2a53a",
    "accent-strong": "#f0b954",
    "accent-subtle": "#362a14",
    "on-accent": "#1c1204",
    "success": "#49b37c",
    "success-subtle": "#16281f",
    "on-success": "#06170e",
    "danger": "#ef5a56",
    "danger-subtle": "#341313",
    "on-danger": "#2a0402",
    "muted": "#8791a3",
    "muted-subtle": "#232732",
}
C = COLORS

# type.groups: nom -> (oila, px, og'irlik). letterSpacing va lineHeight tkinter'da yo'q.
TYPE = {
    "display": ("sans", 28, 600),
    "heading": ("sans", 16, 600),
    "body": ("sans", 13, 400),
    "body-strong": ("sans", 13, 600),
    "label": ("sans", 12, 600),
    "caption": ("sans", 11, 400),
    "stat": ("mono", 13, 600),
    "code": ("mono", 12, 400),
}
FAMILIES = {"sans": ("Segoe UI Variable Text", "Segoe UI"), "mono": ("Cascadia Mono", "Consolas")}

SPACE = {1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32}
RADIUS = {"sm": 4, "md": 6, "lg": 10, "full": 999}
MIN_TARGET = 32      # har qanday bosiladigan element balandligi, CSS px
RING = 4             # focus-ring: 2 px bo'shliq + 2 px accent-strong halqa (shadow.focus-ring)

k = 1.0              # DPI masshtabi, init() da aniqlanadi
F = {}               # nom -> tkfont.Font


def px(v):
    """CSS px -> ekran px."""
    return int(round(v * k))


def sp(n):
    return px(SPACE[n])


def _pick(families, want):
    for w in want:
        if w in families:
            return w
    return want[-1]


def _semibold(families, fam):
    for name in (f"{fam} Semibold", f"{fam} SemiBold"):
        if name in families:
            return name, "normal"
    if fam.startswith("Segoe UI") and "Segoe UI Semibold" in families:
        return "Segoe UI Semibold", "normal"
    return fam, "bold"


def init(root):
    """Masshtab, shriftlar, oyna foni, ttk uslublari. Qayta chaqirilsa ham xavfsiz."""
    global k
    k = max(1.0, root.winfo_fpixels("1i") / 96.0)
    fams = set(tkfont.families(root))
    for name, (group, size, weight) in TYPE.items():
        fam = _pick(fams, FAMILIES[group])
        fam, w = _semibold(fams, fam) if weight >= 600 else (fam, "normal")
        F[name] = tkfont.Font(root=root, family=fam, size=-px(size), weight=w)
    root.configure(bg=C["surface-100"])
    root.option_add("*Font", F["body"])
    try:                                   # oyna va vazifalar panelidagi logotip (tools/make_icon.py)
        root.iconbitmap(default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                             "assets", "eyecontact.ico"))
    except tk.TclError:
        pass

    st = ttk.Style(root)
    st.theme_use("clam")
    # Ingichka, strelkasiz scrollbar: trough panel rangida, thumb surface-400
    st.layout("EC.Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
        ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    st.configure("EC.Vertical.TScrollbar", troughcolor=C["surface-200"], background=C["surface-400"],
                 bordercolor=C["surface-200"], lightcolor=C["surface-400"], darkcolor=C["surface-400"],
                 relief="flat", borderwidth=0, arrowsize=px(8), gripcount=0)
    st.map("EC.Vertical.TScrollbar", background=[("pressed", C["border-strong"]), ("active", C["border-strong"])],
           lightcolor=[("pressed", C["border-strong"]), ("active", C["border-strong"])],
           darkcolor=[("pressed", C["border-strong"]), ("active", C["border-strong"])])
    _dark_titlebar(root)


def _dark_titlebar(root):
    """Windows 10/11 sarlavha satrini qorong'i qiladi (DWMWA_USE_IMMERSIVE_DARK_MODE). Ishlamasa jim o'tadi."""
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        on = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
    except Exception:
        pass


def mix(a, b, t):
    """Ikki hex rang orasida chiziqli aralash, t=0 -> a, t=1 -> b."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def widget_bg(w):
    try:
        return w.cget("bg")
    except tk.TclError:
        return C["surface-100"]
