"""Baholash: original + natija + report.json -> metrics.json, PASS/FAIL (TEXNIK_TOPSHIRIQ 10-bo'lim).

    runtime\\python\\python.exe tools\\eval.py ORIGINAL RESULT REPORT.json [--out metrics.json] [--step 5]

Dasturchi vositasi. Kerak: requirements-eval.txt (onnxruntime, mediapipe) va models/ papkasida modellar (yo'q bo'lsa
tegishli metrika SKIP): w600k_r50.onnx (insightface buffalo_l), face_landmarker.task (MediaPipe), resnet34_gaze.onnx.

Estimatorlar (Maxine'dan mustaqil bo'lishi uchun):
  - gaze: Gaze360 ResNet-34 (yakhyo/gaze-estimation ONNX, models/resnet34_gaze.onnx), har --step kadrda.
    INFO: kichik yuzda (ko'z ~85 px) estimatorlar ±7° sochiladi, gaze_success verdictga kirmaydi, faqat hisobotda.
  - ear_drift: MediaPipe FaceLandmarker (yuz crop, 2x), har --step kadrda; blink soni: Maxine 68-pt EAR har kadrda
  - identity: ArcFace w600k_r50 (ONNX, CPU), ikkala kadr ORIGINAL landmarklar bilan tekislanadi
  - mask_leak: faqat lossless (ffv1) natijada
Chiqish kodi: 0 PASS, 2 FAIL.
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from eyecontact import video_io  # noqa: E402
from eyecontact.maxine import GazeRedirector  # noqa: E402

ARCFACE = os.path.join(ROOT, "models", "w600k_r50.onnx")
MP_MODEL = os.path.join(ROOT, "models", "face_landmarker.task")
G360 = os.path.join(ROOT, "models", "resnet34_gaze.onnx")
ARCFACE_DST = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                        [41.5493, 92.3655], [70.7299, 92.2041]], np.float32)
MIN_CONF = 0.15
# ear_drift 0.15: foydalanuvchi 2026-09-18 da --lid-open 0.5 ni tanladi (yuqori qovoq ko'tariladi, EAR ~+12%)
THRESH = {"identity_median": (">=", 0.97), "identity_min": (">=", 0.93), "ear_drift": ("<=", 0.15),
          "blink_count_ratio": ("range", (0.95, 1.05)), "flicker_ratio": ("<=", 1.5),
          "frame_count_equal": ("==", True), "duration_diff_frames": ("<=", 1.0), "audio_hash_equal": ("==", True),
          "mask_leak": ("<=", 0), "av_offset_frames": ("<=", 1.0)}
INFO = {"gaze_success": (">=", 0.90)}  # hisobotda, verdictga kirmaydi


def audio_md5(path):
    r = subprocess.run([video_io.FFMPEG, "-v", "error", "-i", path, "-map", "0:a:0?", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def av_offset_ms(mi, mr):
    """(video - audio start_time) chiqishda minus kirishda, ms. Audio yo'q bo'lsa None."""
    if mi["audio_codec"] is None or mr["audio_codec"] is None:
        return None
    off = lambda m: m["start_time"] - m["audio_start_time"]
    return round((off(mr) - off(mi)) * 1000, 2)


def ear68(lm):
    """68-pt landmark -> o'rtacha EAR. Ko'z: 36-41, 42-47."""
    def one(p):
        return (np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])) / (2 * np.linalg.norm(p[0] - p[3]) + 1e-6)
    return (one(lm[36:42]) + one(lm[42:48])) / 2


class Gaze360:
    """yakhyo/gaze-estimation ONNX: yuz crop (bbox x1.3) -> 448x448 RGB ImageNet norm -> 90 bin x 4° -> yaw, pitch (°)."""
    IDX = np.arange(90, dtype=np.float32)

    def __init__(self, path=G360):
        import onnxruntime as ort
        self.s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        self.inp = self.s.get_inputs()[0].name

    def angles(self, bgr, bbox):
        h, w = bgr.shape[:2]
        x, y, bw, bh = bbox
        sz = max(bw, bh) * 1.3
        x0, y0 = int(max(0, x + bw / 2 - sz / 2)), int(max(0, y + bh / 2 - sz / 2))
        x1, y1 = int(min(w, x + bw / 2 + sz / 2)), int(min(h, y + bh / 2 + sz / 2))
        im = cv2.cvtColor(cv2.resize(bgr[y0:y1, x0:x1], (448, 448)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        im = ((im - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).astype(np.float32).transpose(2, 0, 1)[None]
        yaw, pitch = self.s.run(None, {self.inp: im})

        def ang(l):
            p = np.exp(l - l.max())
            return float((p / p.sum() * self.IDX).sum() * 4 - 180)
        return ang(yaw[0]), ang(pitch[0])


def five_points(lm):
    return np.array([lm[36:42].mean(0), lm[42:48].mean(0), lm[30], lm[48], lm[54]], np.float32)


class ArcFace:
    def __init__(self, path=ARCFACE):
        import onnxruntime as ort
        self.s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        self.inp = self.s.get_inputs()[0].name

    def embed(self, bgr, lm):
        M, _ = cv2.estimateAffinePartial2D(five_points(lm), ARCFACE_DST, method=cv2.LMEDS)
        face = cv2.warpAffine(bgr, M, (112, 112), borderValue=0)
        x = cv2.cvtColor(face, cv2.COLOR_BGR2RGB).astype(np.float32)
        x = ((x - 127.5) / 127.5).transpose(2, 0, 1)[None]
        e = self.s.run(None, {self.inp: x})[0][0]
        return e / (np.linalg.norm(e) + 1e-9)


class MpEar:
    """MediaPipe FaceLandmarker: yuz crop (Maxine bbox x1.8, kichik bo'lsa 2x) -> EAR (ikki ko'z o'rtachasi)."""
    EYES = ((133, 33, 159, 145), (362, 263, 386, 374))

    def __init__(self, path=MP_MODEL):
        import mediapipe as mp
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        self.mp = mp
        self.lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=mpp.BaseOptions(model_asset_path=path), running_mode=vision.RunningMode.IMAGE, num_faces=1))

    def ear(self, bgr, bbox):
        h, w = bgr.shape[:2]
        x, y, bw, bh = bbox
        s = max(bw, bh) * 1.8
        x0, y0 = int(max(0, x + bw / 2 - s / 2)), int(max(0, y + bh / 2 - s / 2))
        x1, y1 = int(min(w, x + bw / 2 + s / 2)), int(min(h, y + bh / 2 + s / 2))
        crop = bgr[y0:y1, x0:x1]
        if crop.shape[0] < 600:
            crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                            data=np.ascontiguousarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
        r = self.lm.detect(img)
        if not r.face_landmarks:
            return None
        P = np.array([[p.x * crop.shape[1], p.y * crop.shape[0]] for p in r.face_landmarks[0]])
        return float(np.mean([abs(P[lo, 1] - P[up, 1]) / (abs(P[o, 0] - P[i, 0]) + 1e-6) for i, o, up, lo in self.EYES]))


def count_blinks(ears, thr, min_len=2):
    n, run = 0, 0
    for e in ears:
        if e is not None and e < thr:
            run += 1
        else:
            n += run >= min_len
            run = 0
    return n + (run >= min_len)


def mask_leak(orig, result, boxes, meta):
    w, h, fps = meta["width"], meta["height"], meta["fps"]
    ra = video_io.FrameReader(orig, w, h, fps, pix_fmt="yuv420p")
    rb = video_io.FrameReader(result, w, h, fps, pix_fmt="yuv420p")
    n, leak = w * h, 0
    for i, (fa, fb) in enumerate(zip(ra, rb)):
        Ya, Yb = fa[:n].reshape(h, w).copy(), fb[:n].reshape(h, w).copy()
        Ca, Cb = fa[n:].reshape(2, h // 2, w // 2).copy(), fb[n:].reshape(2, h // 2, w // 2).copy()
        box = boxes[i] if i < len(boxes) else None
        if box:
            x0, y0, x1, y1 = box
            Ya[y0:y1, x0:x1] = Yb[y0:y1, x0:x1] = 0
            Ca[:, y0 // 2:y1 // 2, x0 // 2:x1 // 2] = Cb[:, y0 // 2:y1 // 2, x0 // 2:x1 // 2] = 0
        leak += int(np.count_nonzero(Ya != Yb)) + int(np.count_nonzero(Ca != Cb))
    return leak


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("result")
    ap.add_argument("report")
    ap.add_argument("--out", default=None, help="default RESULT.metrics.json")
    ap.add_argument("--step", type=int, default=5, help="identity va MediaPipe EAR har N-kadrda (default 5)")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--no-identity", action="store_true")
    a = ap.parse_args(argv)

    with open(a.report, encoding="utf-8") as f:
        rep = json.load(f)
    changed, boxes = rep["per_frame"]["changed"], rep["per_frame"]["box"]
    mi, mr = video_io.probe(a.original), video_io.probe(a.result)
    w, h, fps = mi["width"], mi["height"], mi["fps"]
    m = {"estimators": {"gaze": "gaze360 resnet34 (INFO)", "ear_drift": "mediapipe", "blink": "maxine 68-pt EAR",
                        "identity": "arcface w600k_r50"},
         "frame_count_in": mi["nb_frames"], "frame_count_out": mr["nb_frames"],
         "frame_count_equal": mi["nb_frames"] == mr["nb_frames"],
         "duration_diff_frames": round(abs(mi["duration"] - mr["duration"]) * float(fps), 2),
         "audio_hash_equal": audio_md5(a.original) == audio_md5(a.result),
         "frames_processed": int(sum(changed))}
    m["mask_leak"] = mask_leak(a.original, a.result, boxes, mi) if mr["codec"] == "ffv1" else None
    # EC-1: chiqishdagi (video - audio) start_time farqi kirishdagidan qancha farq qiladi; chegara ±1 kadr
    m["av_offset_ms"] = av_offset_ms(mi, mr)
    m["av_offset_frames"] = round(abs(m["av_offset_ms"]) * float(fps) / 1000, 2) if m["av_offset_ms"] is not None else None

    matrix, full = video_io.color_params(mi)
    ro = video_io.FrameReader(a.original, w, h, fps, count=a.max_frames, matrix=matrix, full=full)
    rr = video_io.FrameReader(a.result, w, h, fps, count=a.max_frames, matrix=matrix, full=full)
    arc = ArcFace() if not a.no_identity and os.path.exists(ARCFACE) else None
    try:
        mpe = MpEar() if os.path.exists(MP_MODEL) else None
    except ImportError:
        mpe = None
    try:
        g360 = Gaze360() if os.path.exists(G360) else None
    except ImportError:
        g360 = None
    ears_o, ears_r, sims, fl_o, fl_r = [], [], [], [], []
    g_o, g_r, mx_o, mx_r, drift = [], [], [], [], []
    prev_o = prev_r = None
    with GazeRedirector(w, h, temporal=False, redirect=False) as est:
        for i, (fo, fr) in enumerate(zip(ro, rr)):
            _, io = est.run(fo)
            _, ir = est.run(fr)
            ok = io["conf"] >= MIN_CONF and ir["conf"] >= MIN_CONF
            ears_o.append(float(ear68(io["landmarks"])) if ok else None)
            ears_r.append(float(ear68(ir["landmarks"])) if ok else None)
            proc = i < len(changed) and changed[i] and ok
            if proc:
                lm = io["landmarks"]
                mx_o.append((io["gaze_yaw"], io["gaze_pitch"]))
                mx_r.append((ir["gaze_yaw"], ir["gaze_pitch"]))
                if i % a.step == 0:
                    if arc:
                        sims.append(float(np.dot(arc.embed(fo, lm), arc.embed(fr, lm))))
                    if mpe:
                        eo, er = mpe.ear(fo, io["bbox"]), mpe.ear(fr, io["bbox"])
                        if eo and er:
                            drift.append(abs(er - eo) / eo)
                    if g360:
                        g_o.append(g360.angles(fo, io["bbox"]))
                        g_r.append(g360.angles(fr, io["bbox"]))
            if prev_o is not None and i < len(boxes) and boxes[i] and boxes[i - 1]:
                x0 = min(boxes[i][0], boxes[i - 1][0]); y0 = min(boxes[i][1], boxes[i - 1][1])
                x1 = max(boxes[i][2], boxes[i - 1][2]); y1 = max(boxes[i][3], boxes[i - 1][3])
                fl_o.append(float(np.abs(fo[y0:y1, x0:x1].astype(np.int16) - prev_o[y0:y1, x0:x1]).mean()))
                fl_r.append(float(np.abs(fr[y0:y1, x0:x1].astype(np.int16) - prev_r[y0:y1, x0:x1]).mean()))
            prev_o, prev_r = fo.astype(np.int16), fr.astype(np.int16)
            if i % 500 == 0:
                print(f"kadr {i}", file=sys.stderr, flush=True)

    if not drift:  # MediaPipe yo'q: Maxine EAR
        drift = [abs(r - o) / o for o, r, c in zip(ears_o, ears_r, changed) if o and r and c]
        m["estimators"]["ear_drift"] = "maxine 68-pt EAR"
    eo = np.array([e for e in ears_o if e is not None])
    thr = 0.6 * float(np.median(eo)) if len(eo) else 0.2
    g_o, g_r, mx_o, mx_r = (np.array(x).reshape(-1, 2) for x in (g_o, g_r, mx_o, mx_r))
    med = lambda arr: [round(float(v), 1) for v in np.median(arr, axis=0)] if len(arr) else None
    m.update({
        "ear_median_in": round(float(np.median(eo)), 4) if len(eo) else None, "blink_thr": round(thr, 4),
        "ear_drift": round(float(np.median(drift)), 4) if drift else None,
        "blink_count_in": count_blinks(ears_o, thr), "blink_count_out": count_blinks(ears_r, thr),
        "gaze360_yaw_pitch_in": med(g_o), "gaze360_yaw_pitch_out": med(g_r),
        "gaze_success": round(float(np.mean((np.abs(g_r[:, 0]) <= 5) & (np.abs(g_r[:, 1]) <= 5))), 4) if len(g_r) else None,
        "maxine_yaw_pitch_in": med(mx_o), "maxine_yaw_pitch_out": med(mx_r),
        "identity_median": round(float(np.median(sims)), 4) if sims else None,
        "identity_min": round(float(np.min(sims)), 4) if sims else None,
        "flicker_in": round(float(np.mean(fl_o)), 4) if fl_o else None,
        "flicker_out": round(float(np.mean(fl_r)), 4) if fl_r else None,
    })
    m["blink_count_ratio"] = (round(m["blink_count_out"] / m["blink_count_in"], 4) if m["blink_count_in"] else None)
    m["flicker_ratio"] = round(m["flicker_out"] / m["flicker_in"], 4) if fl_o and m["flicker_in"] else None

    results = {}
    for k, (op, ref) in {**THRESH, **INFO}.items():
        v = m.get(k)
        if v is None:
            results[k] = "SKIP"
            continue
        ok = {">=": lambda: v >= ref, "<=": lambda: v <= ref, "==": lambda: v == ref,
              "range": lambda: ref[0] <= v <= ref[1]}[op]()
        results[k] = ("PASS" if ok else "FAIL") if k in THRESH else ("INFO-ok" if ok else "INFO-low")
    m["results"] = results
    m["verdict"] = "FAIL" if "FAIL" in results.values() else "PASS"
    outp = a.out or a.result + ".metrics.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    for k, r in results.items():
        print(f"{k:22s} {r:8s} {m.get(k)}")
    print(f"gaze360 yaw/pitch in {m['gaze360_yaw_pitch_in']} -> out {m['gaze360_yaw_pitch_out']}; "
          f"maxine in {m['maxine_yaw_pitch_in']} -> out {m['maxine_yaw_pitch_out']}")
    print(f"NATIJA: {m['verdict']}  ({outp})")
    return 0 if m["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
