"""GazeRedirector o'rnini bosuvchi stub (EC-5): Maxine/GPU'siz pipeline testlari uchun.

modify=False: kadrni o'zgartirmaydi, conf=0 (yuz yo'q) -> pipeline kirish baytlarini o'zgarishsiz yozishi kerak.
modify=True: yuz "topiladi" (conf=1), ko'z hududidagi piksellar kadrga bog'liq tarzda o'zgartiriladi -> patch yo'li
(diff box, lid_mask, IrisTone, paste_patch) GPU'siz ishlaydi va natija deterministik.
"""
import numpy as np


class StubGazeRedirector:
    def __init__(self, width, height, *, redirect=True, modify=False, **_kw):
        self.w, self.h, self.redirect, self.modify = width, height, redirect, modify
        cx, cy = width / 2, height * 0.4
        self.bbox = (cx - height * 0.25, cy - height * 0.3, height * 0.5, height * 0.6)  # FaceROI: S=1
        lm = np.tile(np.array([cx, cy], np.float32), (68, 1))
        hexagon = np.array([[-12, 0], [-6, -4], [6, -4], [12, 0], [6, 4], [-6, 4]], np.float32)
        lm[36:42] = hexagon + (cx - 30, cy)
        lm[42:48] = hexagon + (cx + 30, cy)
        self.lm = lm
        # o'zgartiriladigan to'rtburchak (ko'zlar atrofi)
        self.rect = (int(cx - 46), int(cy - 10), int(cx + 46), int(cy + 10))

    def run(self, frame, out=None):
        if out is None:
            out = np.empty_like(frame)
        out[:] = frame
        found = self.modify
        if found and self.redirect:
            x0, y0, x1, y1 = self.rect
            out[y0:y1, x0:x1] = 255 - frame[y0:y1, x0:x1]
        info = {"gaze_pitch": 0.0, "gaze_yaw": 0.0, "head_yaw": 0.0, "head_pitch": 0.0, "head_roll": 0.0,
                "conf": 1.0 if found else 0.0, "bbox": self.bbox if found else (0, 0, 0, 0),
                "landmarks": self.lm.copy(), "gaze_landmarks": np.zeros((12, 2), np.float32)}
        return out, info

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def install(monkeypatch, modify=False):
    from eyecontact import pipeline

    monkeypatch.setattr(pipeline, "GazeRedirector",
                        lambda w, h, **kw: StubGazeRedirector(w, h, modify=modify, **kw))
