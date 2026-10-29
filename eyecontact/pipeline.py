"""Orkestratsiya: chunk -> (decode thread) -> Maxine -> YUV kompozit -> (encode thread); resume; concat; hisobot.

Mask tashqarisi bayt-identik: chiqish kadri = kirishning yuv420p baytlari, faqat Maxine o'zgartirgan
to'rtburchak (diff box) BGR dan YUV ga o'tkazilib joylanadi.
"""
import json
import math
import os
import queue
import shutil
import sys
import threading
import time

import cv2
import numpy as np

from . import patches, video_io
from .maxine import GazeRedirector

WARMUP = 25          # chunk boshida Maxine temporal holatini isitish uchun kadrlar (yozilmaydi)
MIN_CONF = 0.15      # Maxine sample: landmark o'rtacha confidence < 0.15 -> yuz yo'q
SUPPORTED_PIX = ("yuv420p", "yuvj420p")

_K = {"bt709": (0.2126, 0.0722), "bt2020nc": (0.2627, 0.0593)}  # boshqasi: bt601


def bgr_to_yuv420(patch, matrix, full):
    """BGR (juft o'lcham) -> (Y, U, V) uint8 planelar, dekoderdagi matrix/range bilan mos."""
    kr, kb = _K.get(matrix, (0.299, 0.114))
    kg = 1.0 - kr - kb
    b, g, r = (patch[..., i].astype(np.float32) / 255.0 for i in range(3))
    y = kr * r + kg * g + kb * b
    u = (b - y) / (2.0 * (1.0 - kb))
    v = (r - y) / (2.0 * (1.0 - kr))
    if full:
        Y, U, V = y * 255.0, 128.0 + u * 255.0, 128.0 + v * 255.0
    else:
        Y, U, V = 16.0 + y * 219.0, 128.0 + u * 224.0, 128.0 + v * 224.0
    h, w = y.shape
    U = U.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
    V = V.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
    q = lambda a: np.clip(np.rint(a), 0, 255).astype(np.uint8)
    return q(Y), q(U), q(V)


def diff_box(a, b):
    """a, b: HxWx3. O'zgargan piksellarni o'rab turgan juft-tekislangan (x0, y0, x1, y1) yoki None."""
    h, w = a.shape[:2]
    rows = np.flatnonzero((a.reshape(h, -1) != b.reshape(h, -1)).any(axis=1))  # 2D ko'rinish: ~2 ms, HxWx3 any(axis=2): 16 ms
    if not len(rows):
        return None
    band = slice(rows[0], rows[-1] + 1)
    cols = np.flatnonzero((a[band] != b[band]).any(axis=(0, 2)))
    y0, y1 = rows[0] & ~1, min(h, (rows[-1] + 2) & ~1)
    x0, x1 = cols[0] & ~1, min(w, (cols[-1] + 2) & ~1)
    return int(x0), int(y0), int(x1), int(y1)


def lid_mask(box, lm68, lid_open=0.5):
    """Aralashtirish maskasi (0..1, HxWx1) box ichida. Asos: original qovoq konturi (68-pt: 36-41, 42-47) + 1 px.
    lid_open > 0: maska FAQAT YUQORIGA kengayadi. Odam kameraga qaraganda asosan yuqori qovoq ko'tariladi;
    pastki qovoq va ko'z burchaklari original qoladi. O'lchandi (og'ish 7.7 gradus): lid_open 0 -> tuzatish 35%,
    EAR +7%; 0.5 -> 62%, +12%; Maxine xom -> 68%, +15%. eye_w = BITTA ko'z kengligi (test videoda 24 px)."""
    x0, y0, x1, y1 = box
    mk = np.zeros((y1 - y0, x1 - x0), np.uint8)
    eye_w = max(1.0, float(np.ptp(lm68[36:42, 0])))
    for poly in (lm68[36:42], lm68[42:48]):
        cv2.fillPoly(mk, [np.round(poly - (x0, y0)).astype(np.int32)], 255)
    d = max(1, int(round(eye_w * 0.04)))
    mk = cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * d + 1, 2 * d + 1)))
    u = int(round(eye_w * 0.42 * lid_open))          # 24 px ko'z: lid_open 0.5 -> 5 px, 1 -> 10 px
    if u > 0:
        mk = cv2.dilate(mk, np.ones((u + 1, 1), np.uint8), anchor=(0, 0))   # anchor tepada: faqat yuqoriga
    return cv2.GaussianBlur(mk, (0, 0), max(1.0, eye_w * 0.075))[..., None].astype(np.float32) / 255.0


def lid_blend(orig_patch, out_patch, mk):
    o, r = orig_patch.astype(np.float32), out_patch.astype(np.float32)
    return np.clip(o + (r - o) * mk, 0, 255).astype(np.uint8)


class IrisTone:
    """Maxine irisni originaldan kulrangroq chizadi (o'lchandi: ko'z ichidagi 8-percentil yorqinlik 53 -> 78).
    Natijadagi qorong'i tonlarni original darajasiga tushiradi (faqat qoraytiradi, rang nisbati saqlanadi).
    Parametrlar EMA bilan silliqlanadi: kadrdan kadrga miltillamasin."""

    def __init__(self, alpha=0.15):
        self.alpha, self.s = alpha, None

    def apply(self, orig_patch, res_patch, mk):
        inside = mk[..., 0] > 0.5
        if int(inside.sum()) < 20:                   # blink: kontur yopiq
            return res_patch
        yo = cv2.cvtColor(np.ascontiguousarray(orig_patch), cv2.COLOR_BGR2GRAY).astype(np.float32)
        yr = cv2.cvtColor(np.ascontiguousarray(res_patch), cv2.COLOR_BGR2GRAY).astype(np.float32)
        cur = np.array([np.percentile(yo[inside], 8), np.percentile(yr[inside], 8), np.percentile(yr[inside], 85)],
                       np.float32)
        self.s = cur if self.s is None else self.s + self.alpha * (cur - self.s)
        o_lo, r_lo, r_hi = self.s
        if o_lo >= r_lo or r_hi - r_lo < 10:
            return res_patch
        ynew = np.where(yr < r_hi, o_lo + (yr - r_lo) * (r_hi - o_lo) / (r_hi - r_lo), yr)
        gain = np.clip(ynew / np.maximum(yr, 1.0), 0.45, 1.0)[..., None]
        return np.clip(res_patch.astype(np.float32) * (1.0 - mk + mk * gain), 0, 255).astype(np.uint8)


class FaceROI:
    """Yuz kichik bo'lsa Maxine'ga S marta kattalashtirilgan crop beriladi: iris aniqroq chiqadi
    (o'lchandi: 230 px yuzda to'g'ridan berilganda iris kulrang/xira). S butun son va w, h ni bo'ladi,
    ROI juft koordinatada: natija original piksel to'riga aniq tushadi. ROI gisterezis bilan kam qimirlaydi."""

    TARGET = 0.6  # kattalashtirilgandan keyin yuz balandligi / kadr balandligi

    def __init__(self, w, h, max_scale=4):
        self.w, self.h = w, h
        self.scales = [s for s in range(1, max_scale + 1) if w % (2 * s) == 0 and h % (2 * s) == 0]
        self.S, self.x0, self.y0, self.valid = 1, 0, 0, False

    def size(self):
        return self.w // self.S, self.h // self.S

    def update(self, bbox, lm68=None):
        """bbox, lm68 original koordinatada. ROI o'zgarsa True.
        ROI ko'zlar o'rtasiga markazlanadi: Maxine nigoh burchagini rasm markaziga nisbatan o'lchaydi
        (o'lchandi: ko'z 300 px chetda -> o'qish ~15 gradusga siljiydi, ichki 20/30 gradus chegaralari noto'g'ri ishlaydi)."""
        x, y, bw, bh = bbox
        if bw <= 0 or bh <= 0:
            return False
        r = self.TARGET * self.h / bh
        S = self.S
        if not self.valid or not (S - 0.75 <= r <= S + 0.75):
            S = min(self.scales, key=lambda s: abs(s - r))
        cw, ch = self.w // S, self.h // S
        cx, cy = (x + bw / 2, y + bh / 2) if lm68 is None else lm68[36:48].mean(axis=0)
        if (self.valid and S == self.S and abs(cx - (self.x0 + cw / 2)) <= 0.08 * cw
                and abs(cy - (self.y0 + ch / 2)) <= 0.08 * ch):
            return False
        self.S = S
        self.x0 = int(np.clip(cx - cw / 2, 0, self.w - cw)) & ~1
        self.y0 = int(np.clip(cy - ch / 2, 0, self.h - ch)) & ~1
        self.valid = True
        return True


def redirect_frame(fb, gz, det, roi, out_buf):
    """Bitta kadr -> (patch, box, info). patch = box ichidagi yangi BGR; info original koordinatada.
    O'zgarish yo'q yoki yuz yo'q bo'lsa patch va box None."""
    h, w = fb.shape[:2]
    if roi is not None and not roi.valid:
        _, di = det.run(fb)
        if di["conf"] >= MIN_CONF:
            roi.update(di["bbox"], di["landmarks"])
    if roi is None or not roi.valid or roi.S == 1:
        _, info = gz.run(fb, out_buf)
        if roi is not None and info["conf"] >= MIN_CONF:
            roi.update(info["bbox"], info["landmarks"])
        box = diff_box(fb, out_buf) if info["conf"] >= MIN_CONF else None
        return (out_buf[box[1]:box[3], box[0]:box[2]] if box else None), box, info
    S, x0, y0 = roi.S, roi.x0, roi.y0
    cw, ch = roi.size()
    up = cv2.resize(fb[y0:y0 + ch, x0:x0 + cw], (w, h), interpolation=cv2.INTER_CUBIC)
    _, info = gz.run(up, out_buf)
    if info["conf"] < MIN_CONF:          # yuz ROI dan chiqqan bo'lishi mumkin: keyingi kadrda qayta aniqlanadi
        roi.valid = False
        return None, None, info
    for k in ("landmarks", "gaze_landmarks"):
        info[k] = info[k] / S + (x0, y0)
    bx, by, bw, bh = info["bbox"]
    info["bbox"] = (bx / S + x0, by / S + y0, bw / S, bh / S)
    roi.update(info["bbox"], info["landmarks"])
    ub = diff_box(up, out_buf)
    if not ub:
        return None, None, info
    q = 2 * S                             # juft original koordinataga tushishi uchun
    ux0, uy0 = (ub[0] // q) * q, (ub[1] // q) * q
    ux1, uy1 = min(w, -(-ub[2] // q) * q), min(h, -(-ub[3] // q) * q)
    delta = out_buf[uy0:uy1, ux0:ux1].astype(np.float32) - up[uy0:uy1, ux0:ux1]
    delta = cv2.resize(delta, ((ux1 - ux0) // S, (uy1 - uy0) // S), interpolation=cv2.INTER_AREA)
    box = (x0 + ux0 // S, y0 + uy0 // S, x0 + ux1 // S, y0 + uy1 // S)
    # faqat delta qo'shiladi: Maxine tegmagan piksel (delta 0) original bo'lib qoladi
    patch = np.clip(np.rint(fb[box[1]:box[3], box[0]:box[2]] + delta), 0, 255).astype(np.uint8)
    return patch, box, info


def paste_patch(yuv, w, h, bgr, box, matrix, full, orig=None):
    """Patch ni yuv420p kadrga yozadi. orig (box ichidagi original BGR) berilsa, faqat o'zgargan piksellar yoziladi:
    Y - o'zgargan piksel, U/V - kamida bitta o'zgargan pikselli 2x2 blok. Qolgani kirish baytlari bo'lib qoladi.
    (orig siz: BGR->YUV qayta konvertatsiya box ichidagi o'zgarmagan piksellarni ham siljitardi: Y max 10, UV max 22.)"""
    x0, y0, x1, y1 = box
    Y = yuv[: w * h].reshape(h, w)
    n = w * h
    U = yuv[n: n + (w // 2) * (h // 2)].reshape(h // 2, w // 2)
    V = yuv[n + (w // 2) * (h // 2):].reshape(h // 2, w // 2)
    patch = bgr if bgr.shape[:2] == (y1 - y0, x1 - x0) else bgr[y0:y1, x0:x1]
    py, pu, pv = bgr_to_yuv420(patch, matrix, full)
    ys, cs = (slice(y0, y1), slice(x0, x1)), (slice(y0 // 2, y1 // 2), slice(x0 // 2, x1 // 2))
    if orig is None:
        Y[ys], U[cs], V[cs] = py, pu, pv
        return
    ch = (patch != orig).any(axis=2)
    cc = ch.reshape(ch.shape[0] // 2, 2, ch.shape[1] // 2, 2).any(axis=(1, 3))
    Y[ys] = np.where(ch, py, Y[ys])
    U[cs] = np.where(cc, pu, U[cs])
    V[cs] = np.where(cc, pv, V[cs])


def log(msg, quiet=False):
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


class Config:
    def __init__(self, **kw):
        self.chunk_sec = 120
        self.resume = False
        self.codec = "h264"
        self.bitrate = None        # None -> kirish bitrate x1.5; 0 -> cq
        self.cq = 18
        self.lossless = False
        self.workdir = None
        self.keep_work = False
        self.eye_size = 2
        self.blend = "lid"         # lid: original qovoq konturi ichida; box: Maxine xom (ko'z kattalashishi mumkin)
        self.lid_open = 0.5        # 0..1: yuqori qovoq qanchalik ochilishi (foydalanuvchi 0.5 ni tanladi, 2026-09-18)
        self.iris_tone = True      # Maxine kulrang chizgan irisni original toniga qaytarish
        self.upscale = True        # kichik yuzni Maxine'ga kattalashtirib berish
        self.temporal = True
        self.max_head_yaw = 30.0
        self.max_head_pitch = 20.0
        self.max_gaze = 30.0
        self.quiet = False
        self.on_progress = None    # callable(done_frames, total_frames), UI uchun
        self.patches_out = None    # papka: video o'rniga ko'z patchlari (EC-4)
        self.input_id = None       # run() to'ldiradi: video_io.file_id(kirish) (EC-3)
        self.__dict__.update(kw)

    def key(self):
        """Natijaga ta'sir qiladigan sozlamalar. Resume faqat shu kalit bir xil bo'lgan chunklarni qayta ishlatadi."""
        names = ("input_id", "chunk_sec", "codec", "bitrate", "cq", "lossless", "eye_size", "blend", "lid_open",
                 "iris_tone", "upscale", "temporal", "max_head_yaw", "max_head_pitch", "max_gaze")
        return "|".join(f"{n}={getattr(self, n)}" for n in names)


def _reader_thread(rb, ry, q):
    while True:
        fb = rb.read()
        fy = ry.read()
        if fb is None or fy is None:
            break
        q.put((fb, fy))
    q.put(None)


def _writer_thread(wr, q):
    while True:
        f = q.get()
        if f is None:
            break
        wr.write(f)


def process_chunk(inp, seg_path, meta, start, end, gz, det, cfg, color):
    w, h, fps = meta["width"], meta["height"], meta["fps"]
    matrix, full = video_io.color_params(meta)
    warm = min(start, WARMUP)
    rb = video_io.FrameReader(inp, w, h, fps, start - warm, end - start + warm, "bgr24", matrix, full,
                              meta["vfr"], meta["start_time"])
    ry = video_io.FrameReader(inp, w, h, fps, start - warm, end - start + warm, "yuv420p", matrix, full,
                              meta["vfr"], meta["start_time"])
    qin, qout = queue.Queue(maxsize=8), queue.Queue(maxsize=8)
    patch_mode = bool(cfg.patches_out)   # EC-4: encode yo'q, faqat o'zgargan YUV baytlar seg_path (.npz) ga
    precs = []
    threading.Thread(target=_reader_thread, args=(rb, ry, qin), daemon=True).start()
    if not patch_mode:
        bitrate = None if cfg.lossless else (cfg.bitrate if cfg.bitrate is not None else int(meta["bit_rate"] * 1.5) or None)
        wr = video_io.FrameWriter(seg_path, w, h, fps, pix_fmt="yuv420p", bitrate=bitrate or None, cq=cfg.cq,
                                  codec=cfg.codec, color=color, lossless=cfg.lossless)
        tw = threading.Thread(target=_writer_thread, args=(wr, qout), daemon=True)
        tw.start()
    rec = {k: [] for k in ("gaze_yaw", "gaze_pitch", "head_yaw", "head_pitch", "conf", "changed", "box")}
    out = np.empty((h, w, 3), np.uint8)
    roi = FaceROI(w, h) if cfg.upscale else None   # har chunk boshida qayta aniqlanadi: resume deterministik
    tone = IrisTone() if cfg.iris_tone else None
    i = -warm
    while True:
        item = qin.get()
        if item is None:
            break
        fb, fy = item
        patch, box, info = redirect_frame(fb, gz, det, roi, out)
        if box:                                        # warm-up kadrlarda ham: IrisTone holati isiydi
            o = fb[box[1]:box[3], box[0]:box[2]]
            mk = lid_mask(box, info["landmarks"], cfg.lid_open if cfg.blend == "lid" else 1.0)
            if cfg.blend == "lid":
                patch = lid_blend(o, patch, mk)
            if tone:
                patch = tone.apply(o, patch, mk)
        if i >= 0:
            if box:
                before = patches.snapshot(fy, w, h, box) if patch_mode else None
                paste_patch(fy, w, h, patch, box, matrix, full, orig=o)
                if patch_mode:
                    precs.append(patches.record(start + i, box, before, fy, w, h))
            if not patch_mode:
                qout.put(fy)
            for k in ("gaze_yaw", "gaze_pitch", "head_yaw", "head_pitch", "conf"):
                rec[k].append(round(float(info[k]), 2))
            rec["changed"].append(bool(box))
            rec["box"].append(box)
            if cfg.on_progress and i % 50 == 0:
                cfg.on_progress(start + i, cfg.total_frames)
        i += 1
    if patch_mode:
        patches.write_chunk(seg_path, precs)
    else:
        qout.put(None)
        tw.join()
        wr.close()
    n = len(rec["changed"])
    if n != end - start:
        raise RuntimeError(f"chunk {start}-{end}: kutilgan {end - start} kadr, dekoddan {n} keldi")
    return rec


def run(inp, out, cfg, max_frames=None):
    """out: natija video. cfg.patches_out berilsa (EC-4) out ishlatilmaydi: video encode qilinmaydi, papkaga
    chunk_XXXXX.npz (patches.py formati) + meta.json yoziladi."""
    t0 = time.time()
    patch_mode = bool(cfg.patches_out)
    meta = video_io.probe(inp)
    if meta["pix_fmt"] not in SUPPORTED_PIX:
        raise SystemExit(f"xato: pix_fmt {meta['pix_fmt']} qo'llanmaydi (faqat 8-bit 4:2:0: {SUPPORTED_PIX})")
    if meta["vfr"]:
        log(f"ogohlantirish: o'zgaruvchan fps (VFR), CFR ga o'tkaziladi: {meta['nb_frames']} kadr "
            f"(davomiylik x fps); tushgan kadrlar o'rnini oldingi kadr to'ldiradi", cfg.quiet)
    if patch_mode:
        out = cfg.patches_out
    elif cfg.lossless and not out.lower().endswith(".mkv"):
        out += ".mkv"
        log(f"ogohlantirish: lossless FFV1 -> MKV: {out}", cfg.quiet)
    safe = out if patch_mode else video_io.safe_container(out, meta["audio_codec"])
    if safe != out:
        log(f"ogohlantirish: audio {meta['audio_codec']} MP4 ichida ko'p dasturda ovozsiz; chiqish MOV: {safe}", cfg.quiet)
        out = safe
    w, h, fps = meta["width"], meta["height"], meta["fps"]
    total = meta["nb_frames"] if max_frames is None else min(meta["nb_frames"], max_frames)
    cfg.total_frames = total
    cfg.input_id = video_io.file_id(inp)   # resume kaliti: boshqa fayl bilan eski chunk'lar ishlatilmasin
    log(f"kirish: {w}x{h} @ {fps} fps, {total} kadr, {meta['codec']} {meta['pix_fmt']} "
        f"{meta['bit_rate'] // 1000} kbps, audio {meta['audio_codec']}", cfg.quiet)
    color = {k: meta[k] for k in ("color_range", "color_space", "color_primaries", "color_trc")}
    workdir = out if patch_mode else (cfg.workdir or out + ".work")
    os.makedirs(workdir, exist_ok=True)
    chunk = max(1, int(round(cfg.chunk_sec * fps)))
    nchunks = math.ceil(total / chunk)
    ext = ".mkv" if cfg.lossless else ".mp4"
    segments, chunk_recs = [], []
    gz = det = None
    try:
        for k in range(nchunks):
            start, end = k * chunk, min(total, (k + 1) * chunk)
            seg = os.path.join(workdir, f"chunk_{k:05d}.npz" if patch_mode else f"seg_{k:05d}{ext}")
            segj = os.path.splitext(seg)[0] + ".json" if patch_mode else seg + ".json"
            segments.append(seg)
            if cfg.resume and os.path.exists(seg) and os.path.exists(segj):
                with open(segj, encoding="utf-8") as f:
                    r = json.load(f)
                if r.get("start") == start and r.get("end") == end and r.get("cfg_key") == cfg.key():
                    log(f"chunk {k + 1}/{nchunks}: tayyor (resume), o'tkazildi", cfg.quiet)
                    if cfg.on_progress:
                        cfg.on_progress(end, total)
                    chunk_recs.append(r)
                    continue
            if gz is None:
                det = GazeRedirector(w, h, temporal=False, redirect=False) if cfg.upscale else None
                gz = GazeRedirector(w, h, temporal=cfg.temporal, eye_size_sensitivity=cfg.eye_size,
                                    gaze_thr=(cfg.max_gaze - 10, cfg.max_gaze),
                                    head_pitch_thr=(cfg.max_head_pitch - 5, cfg.max_head_pitch),
                                    head_yaw_thr=(cfg.max_head_yaw - 5, cfg.max_head_yaw))
            tc = time.time()
            rec = process_chunk(inp, seg, meta, start, end, gz, det, cfg, color)
            rec.update(start=start, end=end, cfg_key=cfg.key())
            with open(segj + ".tmp", "w", encoding="utf-8") as f:
                json.dump(rec, f)
            os.replace(segj + ".tmp", segj)
            chunk_recs.append(rec)
            dt = time.time() - tc
            log(f"chunk {k + 1}/{nchunks}: {end - start} kadr, {sum(rec['changed'])} o'zgargan, "
                f"{dt:.1f} s ({(end - start) / dt:.1f} fps)", cfg.quiet)
    finally:
        if gz:
            gz.close()
        if det:
            det.close()
    if patch_mode:
        matrix, full = video_io.color_params(meta)
        pmeta = {"format_version": patches.FORMAT_VERSION, "source": os.path.abspath(inp),
                 "source_id": cfg.input_id, "width": w, "height": h, "fps": str(fps), "nb_frames": total,
                 "pix_fmt": "yuv420p", "source_pix_fmt": meta["pix_fmt"], "color_matrix": matrix,
                 "color_range": "pc" if full else "tv", "vfr": meta["vfr"], "cfg_key": cfg.key(),
                 "chunks": [{"file": os.path.basename(s), "start": r["start"], "end": r["end"],
                             "frames_patched": int(sum(r["changed"]))} for s, r in zip(segments, chunk_recs)]}
        with open(os.path.join(out, "meta.json.tmp"), "w", encoding="utf-8") as f:
            json.dump(pmeta, f, ensure_ascii=False, indent=1)
        os.replace(os.path.join(out, "meta.json.tmp"), os.path.join(out, "meta.json"))
    else:
        video_io.concat(segments, out, audio_from=inp, workdir=workdir,
                        video_offset=meta["start_time"] - meta["format_start_time"])
    per = {k: sum((r[k] for r in chunk_recs), []) for k in ("gaze_yaw", "gaze_pitch", "head_yaw", "head_pitch",
                                                            "conf", "changed", "box")}
    n = len(per["changed"])
    conf = np.array(per["conf"])
    report = {
        "input": os.path.abspath(inp), "output": os.path.abspath(out), "engine": "maxine",
        "frames_total": n, "frames_changed": int(sum(per["changed"])),
        "frames_skipped": n - int(sum(per["changed"])),
        "skip_reasons": {"no_face_or_low_conf": int((conf < MIN_CONF).sum()),
                         "engine_passthrough": int(((conf >= MIN_CONF) & ~np.array(per["changed"], bool)).sum())},
        "gaze_yaw_median": float(np.median(per["gaze_yaw"])) if n else None,
        "gaze_pitch_median": float(np.median(per["gaze_pitch"])) if n else None,
        "seconds": round(time.time() - t0, 1), "fps": round(n / (time.time() - t0), 1),
        "config": {k: v for k, v in vars(cfg).items() if not callable(v)}, "input_meta": {k: (str(v) if k == "fps" else v) for k, v in meta.items()},
        "per_frame": per,
    }
    if not cfg.keep_work and not patch_mode:
        shutil.rmtree(workdir, ignore_errors=True)
    return report
