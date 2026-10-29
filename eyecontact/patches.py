"""Ko'z patchlari fayli (EC-4, Dars Studio TZ 9.7). Encode o'rniga faqat o'zgargan YUV baytlar saqlanadi.

Chunk (chunk_XXXXX.npz, zlib): har patchli kadr uchun
  frame_idx int32[N]       asl videodagi kadr indeksi
  box       int16[N, 4]    x0, y0, x1, y1 (juft), Y tekisligida
  y_mask    uint8          bitpack: har kadr box ichidagi o'zgargan Y piksellar (h*w bit), ketma-ket
  uv_mask   uint8          bitpack: o'zgargan U/V piksellar (box/2 o'lchamida), ketma-ket
  y_data    uint8          o'zgargan Y qiymatlari (maska tartibida)
  uv_data   uint8          har kadr uchun U[maska] keyin V[maska]
  offsets   int64[N+1, 2]  y_data va uv_data dagi har kadr boshi
  size      int32[2]       kadr kengligi, balandligi
"""
import os

import numpy as np

FORMAT_VERSION = 1


def _planes(yuv, w, h):
    n, q = w * h, (w // 2) * (h // 2)
    return yuv[:n].reshape(h, w), yuv[n:n + q].reshape(h // 2, w // 2), yuv[n + q:n + 2 * q].reshape(h // 2, w // 2)


def _views(yuv, w, h, box):
    x0, y0, x1, y1 = box
    Y, U, V = _planes(yuv, w, h)
    cs = (slice(y0 // 2, y1 // 2), slice(x0 // 2, x1 // 2))
    return Y[y0:y1, x0:x1], U[cs], V[cs]


def snapshot(yuv, w, h, box):
    """box ichidagi Y, U, V nusxasi (patch qo'yilishidan oldin)."""
    return tuple(p.copy() for p in _views(yuv, w, h, box))


def record(frame_idx, box, before, yuv, w, h):
    """Patch qo'yilgan kadrdan yozuv: faqat baytlari o'zgargan piksellar."""
    y, u, v = _views(yuv, w, h, box)
    ym = y != before[0]
    uvm = (u != before[1]) | (v != before[2])
    return {"frame_idx": frame_idx, "box": tuple(box), "size": (w, h), "y_mask": ym, "uv_mask": uvm,
            "y_data": y[ym].copy(), "uv_data": np.concatenate([u[uvm], v[uvm]])}


def write_chunk(path, recs):
    """Atomik yozish (tmp + os.replace)."""
    n = len(recs)
    off = np.zeros((n + 1, 2), np.int64)
    for i, r in enumerate(recs):
        off[i + 1] = off[i] + (len(r["y_data"]), len(r["uv_data"]))
    cat = lambda k, dt: np.concatenate([r[k].ravel() for r in recs]).astype(dt) if n else np.zeros(0, dt)
    size = recs[0]["size"] if n else (0, 0)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        np.savez_compressed(f, frame_idx=np.array([r["frame_idx"] for r in recs], np.int32),
                            box=np.array([r["box"] for r in recs], np.int16).reshape(n, 4),
                            y_mask=np.packbits(cat("y_mask", bool)), uv_mask=np.packbits(cat("uv_mask", bool)),
                            y_data=cat("y_data", np.uint8), uv_data=cat("uv_data", np.uint8), offsets=off,
                            size=np.array(size, np.int32))
    os.replace(tmp, path)


def read_chunk(path):
    """write_chunk teskarisi: yozuvlar ro'yxati (maskalar bool massiv)."""
    with np.load(path) as z:
        d = {k: z[k] for k in z.files}
    w, h = (int(v) for v in d["size"])
    ym_all, uvm_all = np.unpackbits(d["y_mask"]).astype(bool), np.unpackbits(d["uv_mask"]).astype(bool)
    recs, yb, cb = [], 0, 0
    for i, fi in enumerate(d["frame_idx"]):
        x0, y0, x1, y1 = (int(v) for v in d["box"][i])
        bh, bw = y1 - y0, x1 - x0
        ym = ym_all[yb:yb + bh * bw].reshape(bh, bw)
        uvm = uvm_all[cb:cb + bh * bw // 4].reshape(bh // 2, bw // 2)
        yb, cb = yb + bh * bw, cb + bh * bw // 4
        (ys, cs), (ye, ce) = d["offsets"][i], d["offsets"][i + 1]
        recs.append({"frame_idx": int(fi), "box": (x0, y0, x1, y1), "size": (w, h), "y_mask": ym, "uv_mask": uvm,
                     "y_data": d["y_data"][ys:ye], "uv_data": d["uv_data"][cs:ce]})
    return recs


def apply(frame_yuv, rec, w=1.0):
    """Patchni yuv420p kadrga (flat uint8, joyida) qo'llaydi: out = orig + w * (patch - orig), faqat maska ichida.
    w = 1 -> Eye Contact'ning o'z chiqishi bilan bayt-aniq; w = 0 -> o'zgarishsiz (rampa uchun)."""
    if w <= 0:
        return frame_yuv
    fw, fh = rec["size"]
    y, u, v = _views(frame_yuv, fw, fh, rec["box"])
    ym, uvm = rec["y_mask"], rec["uv_mask"]
    k = int(uvm.sum())
    pu, pv = rec["uv_data"][:k], rec["uv_data"][k:]
    if w >= 1:
        y[ym], u[uvm], v[uvm] = rec["y_data"], pu, pv
        return frame_yuv
    mix = lambda o, p: np.clip(np.rint(o + w * (p.astype(np.float32) - o)), 0, 255).astype(np.uint8)
    y[ym], u[uvm], v[uvm] = mix(y[ym], rec["y_data"]), mix(u[uvm], pu), mix(v[uvm], pv)
    return frame_yuv
