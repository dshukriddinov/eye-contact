"""Smoke test: 10 s klip, lossless, 3 chunk. Tekshiradi: kadr soni teng, audio o'zgarmagan,
mask (diff box) tashqarisi bayt-identik, chunk chegarasida uzilish yo'q. Ishga tushirish:
    runtime\\python\\python.exe tests\\test_smoke.py
"""
import hashlib
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eyecontact import pipeline, video_io  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CLIP = os.path.join(HERE, "clip_10s.mp4")
OUT = os.path.join(HERE, "_smoke_out.mkv")


def audio_md5(path):
    r = subprocess.run([video_io.FFMPEG, "-v", "error", "-i", path, "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, encoding="utf-8", errors="replace", check=True)
    return r.stdout.strip()


def main():
    # PCM audio MP4 ichida ko'p dasturda ovozsiz: konteyner .mov ga almashishi shart
    assert video_io.safe_container("x.mp4", "pcm_s16le") == "x.mov"
    assert video_io.safe_container("x.mp4", "aac") == "x.mp4"
    assert video_io.safe_container("x.mkv", "pcm_s16le") == "x.mkv"
    # o'zgarmagan patch qaytarilsa kadr baytlari o'zgarmasligi kerak (box ichida ham)
    m0 = video_io.probe(CLIP)
    mx, fr = video_io.color_params(m0)
    fb = next(iter(video_io.FrameReader(CLIP, m0["width"], m0["height"], m0["fps"], count=1, matrix=mx, full=fr)))
    fy = next(iter(video_io.FrameReader(CLIP, m0["width"], m0["height"], m0["fps"], count=1, pix_fmt="yuv420p")))
    box = (922, 202, 1032, 232)
    o = fb[box[1]:box[3], box[0]:box[2]].copy()
    yy = fy.copy()
    pipeline.paste_patch(yy, m0["width"], m0["height"], o.copy(), box, mx, fr, orig=o)
    assert np.array_equal(yy, fy), "o'zgarmagan piksellar qayta yozilgan"
    p2 = o.copy()
    p2[10:12, 50:52] = 255 - p2[10:12, 50:52]
    pipeline.paste_patch(yy, m0["width"], m0["height"], p2, box, mx, fr, orig=o)
    changed_y = int((yy[: m0["width"] * m0["height"]] != fy[: m0["width"] * m0["height"]]).sum())
    assert 0 < changed_y <= 4, changed_y
    cfg = pipeline.Config(chunk_sec=4, lossless=True, quiet=True)
    rep = pipeline.run(CLIP, OUT, cfg)
    meta_in, meta_out = video_io.probe(CLIP), video_io.probe(OUT)
    assert rep["frames_total"] == meta_in["nb_frames"], (rep["frames_total"], meta_in["nb_frames"])
    assert meta_out["nb_frames"] == meta_in["nb_frames"], (meta_out["nb_frames"], meta_in["nb_frames"])
    assert meta_out["width"] == meta_in["width"] and meta_out["height"] == meta_in["height"]
    assert audio_md5(OUT) == audio_md5(CLIP), "audio o'zgargan"
    assert rep["frames_changed"] > 0, "hech bir kadr o'zgarmagan"

    w, h, fps = meta_in["width"], meta_in["height"], meta_in["fps"]
    matrix, full = video_io.color_params(meta_in)
    ra = video_io.FrameReader(CLIP, w, h, fps, pix_fmt="yuv420p", matrix=matrix, full=full)
    rb = video_io.FrameReader(OUT, w, h, fps, pix_fmt="yuv420p", matrix=matrix, full=full)
    leak = 0
    for i, (fa, fb) in enumerate(zip(ra, rb)):
        box = rep["per_frame"]["box"][i]
        Ya, Yb = fa[: w * h].reshape(h, w).copy(), fb[: w * h].reshape(h, w).copy()
        if box:
            x0, y0, x1, y1 = box
            Ya[y0:y1, x0:x1] = 0
            Yb[y0:y1, x0:x1] = 0
            assert np.any(fa != fb), f"kadr {i}: box bor, lekin piksel o'zgarmagan"
        leak += int(np.count_nonzero(Ya != Yb))
        # chroma: box tashqarisi
        n = w * h
        Ca, Cb = fa[n:].reshape(2, h // 2, w // 2).copy(), fb[n:].reshape(2, h // 2, w // 2).copy()
        if box:
            Ca[:, y0 // 2: y1 // 2, x0 // 2: x1 // 2] = 0
            Cb[:, y0 // 2: y1 // 2, x0 // 2: x1 // 2] = 0
        leak += int(np.count_nonzero(Ca != Cb))
    assert i + 1 == meta_in["nb_frames"], i + 1
    assert leak == 0, f"mask_leak: {leak} piksel mask tashqarisida o'zgargan"
    os.remove(OUT)
    print(f"OK: {rep['frames_total']} kadr, {rep['frames_changed']} o'zgargan, mask_leak=0, audio teng, "
          f"{rep['fps']} fps")


if __name__ == "__main__":
    main()
