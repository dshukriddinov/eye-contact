"""Dastur logotipi: assets/eyecontact.ico (+ preview PNG).

Belgi design-system/components/Cover/preview.html dagi motivdan olingan: accent blok ustida konsentrik iris
halqalari, ink qorachiq va viewfinder chiziqchalari. Yangi belgi o'ylab topilmaydi (brand book, Iconography).
Ranglar theme.COLORS (tokens.json, dark) dan. Chizish anti-aliasing'li (signed distance), faqat numpy + stdlib.

    runtime\\python\\python.exe tools\\make_icon.py
"""
import os
import struct
import sys
import zlib

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from eyecontact.theme import COLORS as C  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)
# Cover'dagi koordinatalar: markaz (350,180), halqa radiuslari 24/40/56 (space-2 qadam), stroke 6, qorachiq r=8,
# chiziqchalar 66..80 radius oralig'ida, stroke 4. Motiv qutisi = 160 birlik (chiziqchadan chiziqchagacha).
MOTIF = 160.0
RINGS = ((56, 6, "accent-subtle"), (40, 6, "ink"), (24, 6, "accent-subtle"))
PUPIL = 8
TICKS = (66, 80, 4)


def _rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def _over(dst, alpha, color):
    """alpha (HxW, 0..1) rangni dst (HxWx4, premultiplied emas) ustiga qo'yadi."""
    a = alpha[..., None]
    da = dst[..., 3:4]
    out_a = a + da * (1 - a)
    rgb = (color * a + dst[..., :3] * da * (1 - a)) / np.maximum(out_a, 1e-6)
    dst[..., :3] = rgb
    dst[..., 3:4] = out_a


def render(size):
    """Bitta o'lchamdagi RGBA rasm. Kichik o'lchamda mayda detallar tushiriladi (o'qilishi uchun)."""
    s = size / MOTIF * 0.80                     # motiv kadrning 80% ini egallaydi
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) + 0.5
    cx = cy = size / 2
    img = np.zeros((size, size, 4), np.float32)

    r = size * 0.2                              # yumaloq kvadrat (accent blok)
    pad = size * 0.02
    qx = np.abs(x - cx) - (size / 2 - pad - r)
    qy = np.abs(y - cy) - (size / 2 - pad - r)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r
    _over(img, np.clip(0.5 - d, 0, 1), _rgb(C["accent"]))

    dist = np.hypot(x - cx, y - cy)
    for rad, stroke, color in RINGS:
        if size < 32 and rad == 24:             # ichki tint halqa 16-24 px da qorishib ketadi
            continue
        w = max(1.2, stroke * s)
        _over(img, np.clip(w / 2 + 0.5 - np.abs(dist - rad * s), 0, 1), _rgb(C[color]))
    _over(img, np.clip(0.5 + PUPIL * s - dist, 0, 1), _rgb(C["ink"]))

    if size >= 48:                              # viewfinder chiziqchalari
        r0, r1, stroke = TICKS
        for ax, ay in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            px0, py0 = cx + ax * r0 * s, cy + ay * r0 * s
            px1, py1 = cx + ax * r1 * s, cy + ay * r1 * s
            vx, vy = px1 - px0, py1 - py0
            t = np.clip(((x - px0) * vx + (y - py0) * vy) / max(vx * vx + vy * vy, 1e-6), 0, 1)
            dl = np.hypot(x - (px0 + t * vx), y - (py0 + t * vy))
            _over(img, np.clip(stroke * s / 2 + 0.5 - dl, 0, 1), _rgb(C["ink"]))
    return np.clip(np.dstack([img[..., :3], img[..., 3] * 255]), 0, 255).round().astype(np.uint8)


def png(rgba):
    h, w = rgba.shape[:2]
    raw = np.concatenate([np.zeros((h, 1), np.uint8), rgba.reshape(h, -1)], axis=1).tobytes()

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico(images):
    """PNG-siqilgan ICO (Windows Vista+)."""
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = len(head) + 16 * len(images)
    entries, blobs = b"", b""
    for data, size in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        blobs += data
    return head + entries + blobs


def main():
    out = os.path.join(ROOT, "assets")
    os.makedirs(out, exist_ok=True)
    images = [(png(render(s)), s) for s in SIZES]
    with open(os.path.join(out, "eyecontact.ico"), "wb") as f:
        f.write(ico(images))
    with open(os.path.join(out, "eyecontact.png"), "wb") as f:
        f.write(dict(zip(SIZES, [i[0] for i in images]))[256])
    print("tayyor:", os.path.join(out, "eyecontact.ico"), "|", ", ".join(str(s) for s in SIZES), "px")


if __name__ == "__main__":
    main()
