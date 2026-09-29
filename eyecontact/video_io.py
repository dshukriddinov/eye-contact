"""ffmpeg orqali probe / decode / encode / concat. Kadrlar rawvideo pipe bilan yuriladi."""
import glob
import json
import os
import shutil
import subprocess
from fractions import Fraction

import numpy as np


_RUNTIME_FFMPEG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime", "ffmpeg")


def _find(tool):
    p = os.path.join(_RUNTIME_FFMPEG, tool + ".exe")   # paket ichidagi portativ nusxa birinchi
    if os.path.exists(p):
        return p
    p = shutil.which(tool)
    if p:
        return p
    pat = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\\") + tool + ".exe"
    hits = glob.glob(pat)
    if hits:
        return hits[0]
    raise FileNotFoundError(f"{tool} topilmadi (PATH yoki winget Gyan.FFmpeg)")


FFMPEG, FFPROBE = _find("ffmpeg"), _find("ffprobe")

_NVENC_OK = {}


def nvenc_ok(enc="h264_nvenc"):
    """NVENC shu driver bilan ishlaydimi (1 kadr sinov). Natija keshlanadi."""
    if enc not in _NVENC_OK:
        r = subprocess.run([FFMPEG, "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                            "color=c=gray:s=256x256:r=25:d=0.04", "-c:v", enc, "-f", "null", "-"],
                           capture_output=True, text=True)
        _NVENC_OK[enc] = r.returncode == 0 and "nvenc" not in r.stderr.lower()
    return _NVENC_OK[enc]


def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    fps = Fraction(v["r_frame_rate"])
    dur = float(d["format"].get("duration") or v.get("duration") or 0)
    nb = int(v.get("nb_frames") or 0)
    if not nb:  # MKV kabi konteynerlarda nb_frames yo'q: paketlarni sanaymiz
        r = subprocess.run([FFPROBE, "-v", "error", "-count_packets", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path],
                           capture_output=True, text=True, check=True)
        nb = int(r.stdout.strip() or round(dur * fps))
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"]) % 360
    w, h = int(v["width"]), int(v["height"])
    if rot in (90, 270):  # ffmpeg dekodda avtomatik buradi
        w, h = h, w
    return {
        "width": w, "height": h, "fps": fps, "nb_frames": nb, "duration": dur, "rotation": rot,
        "start_time": float(v.get("start_time") or 0.0),
        "codec": v["codec_name"], "pix_fmt": v.get("pix_fmt"),
        "bit_rate": int(v.get("bit_rate") or d["format"].get("bit_rate") or 0),
        "color_range": v.get("color_range"), "color_space": v.get("color_space"),
        "color_primaries": v.get("color_primaries"), "color_trc": v.get("color_trc"),
        "vfr": v.get("r_frame_rate") != v.get("avg_frame_rate"),
        "audio_codec": a["codec_name"] if a else None,
    }


def safe_container(out, audio_codec):
    """PCM audio MP4 ichida 'ipcm' tegi bilan yoziladi: ko'p player va montaj dasturida ovoz chiqmaydi.
    MOV PCM ni tabiiy qo'llaydi, shuning uchun audio copy saqlanib, konteyner .mov ga almashtiriladi."""
    if audio_codec and audio_codec.startswith("pcm_") and out.lower().endswith((".mp4", ".m4v")):
        return os.path.splitext(out)[0] + ".mov"
    return out


def color_params(meta):
    """(matrix, full_range) — dekoder va bizning BGR->YUV konvert bir xil bo'lishi uchun."""
    cs = meta.get("color_space")
    if cs in ("bt709", "bt2020nc", "smpte170m", "bt470bg"):
        matrix = cs
    else:
        matrix = "bt709" if meta["height"] >= 720 else "smpte170m"
    full = meta.get("color_range") == "pc" or str(meta.get("pix_fmt")).startswith("yuvj")
    return matrix, full


def frame_bytes(width, height, pix_fmt):
    return width * height * 3 if pix_fmt == "bgr24" else width * height * 3 // 2


class FrameReader:
    """Kadrlarni numpy sifatida o'qiydi (bgr24: HxWx3, yuv420p: flat w*h*3/2). start/count kadr indekslarida."""

    def __init__(self, path, width, height, fps, start=0, count=None, pix_fmt="bgr24", matrix="bt709",
                 full=False, cfr=False, start_time=0.0):
        self.w, self.h, self.pix_fmt = width, height, pix_fmt
        self.frame_bytes = frame_bytes(width, height, pix_fmt)
        cmd = [FFMPEG, "-v", "error", "-nostdin"]
        if start:
            # -ss mutlaq stream vaqti: stream start_time + (start - 0.5) kadr -> aynan `start` kadrdan boshlanadi
            cmd += ["-ss", f"{start_time + float((start - Fraction(1, 2)) / fps):.6f}"]
        cmd += ["-i", path]
        if count is not None:
            cmd += ["-frames:v", str(count)]
        rng = "pc" if full else "tv"
        if pix_fmt == "bgr24":
            cmd += ["-vf", f"scale=in_color_matrix={matrix}:in_range={rng}:out_range=pc"]
        cmd += ["-fps_mode", "cfr" if cfr else "passthrough", "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=self.frame_bytes * 4)

    def read(self):
        buf = self.proc.stdout.read(self.frame_bytes)
        if len(buf) < self.frame_bytes:
            self.close()
            return None
        a = np.frombuffer(buf, dtype=np.uint8).copy()
        return a.reshape(self.h, self.w, 3) if self.pix_fmt == "bgr24" else a

    def __iter__(self):
        while True:
            f = self.read()
            if f is None:
                return
            yield f

    def close(self):
        if self.proc.stdout:
            self.proc.stdout.close()
        self.proc.wait()


class FrameWriter:
    """Kadrlarni faylga yozadi. NVENC bo'lmasa CPU x264/x265. audio_from berilsa audio stream copy."""

    def __init__(self, path, width, height, fps, *, pix_fmt="yuv420p", bitrate=None, cq=18, codec="h264",
                 audio_from=None, color=None, lossless=False):
        cflags = []
        for k, flag in (("color_range", "-color_range"), ("color_space", "-colorspace"),
                        ("color_primaries", "-color_primaries"), ("color_trc", "-color_trc")):
            if color and color.get(k) and color[k] != "unknown":
                cflags += [flag, color[k]]
        cmd = [FFMPEG, "-v", "error", "-nostdin", "-y",
               "-f", "rawvideo", "-pix_fmt", pix_fmt, "-s", f"{width}x{height}", "-r", str(fps)]
        if pix_fmt != "bgr24":
            # kirish teglari chiqish bilan bir xil, aks holda ffmpeg 7 range/matrix konvert qo'shadi (baytlar buziladi)
            cmd += cflags
        cmd += ["-i", "-"]
        if audio_from:
            cmd += ["-i", audio_from, "-map", "0:v:0", "-map", "1:a:0?", "-c:a", "copy"]
        if lossless:
            cmd += ["-c:v", "ffv1", "-level", "3", "-pix_fmt", "yuv420p"]
        else:
            enc = {"h264": "h264_nvenc", "hevc": "hevc_nvenc"}[codec]
            if nvenc_ok(enc):
                cmd += ["-c:v", enc, "-preset", "p7", "-tune", "hq", "-pix_fmt", "yuv420p"]
                if bitrate:
                    cmd += ["-rc", "vbr", "-b:v", str(bitrate), "-maxrate", str(int(bitrate * 1.5)),
                            "-bufsize", str(bitrate * 2)]
                else:
                    cmd += ["-rc", "vbr", "-cq", str(cq), "-b:v", "0"]
            else:  # ponytail: NVENC yo'q (driver eski) -> CPU x264/x265
                cmd += ["-c:v", {"h264": "libx264", "hevc": "libx265"}[codec], "-preset", "medium",
                        "-pix_fmt", "yuv420p"]
                if bitrate:
                    cmd += ["-b:v", str(bitrate), "-maxrate", str(int(bitrate * 1.5)), "-bufsize", str(bitrate * 2)]
                else:
                    cmd += ["-crf", str(cq)]
        cmd += cflags
        if path.lower().endswith((".mp4", ".mov")):
            cmd += ["-movflags", "+faststart"]
        cmd += [path]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=frame_bytes(width, height, pix_fmt) * 4)

    def write(self, frame):
        self.proc.stdin.write(memoryview(np.ascontiguousarray(frame)))

    def close(self):
        self.proc.stdin.close()
        rc = self.proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg encode xato, kod {rc}")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def concat(segments, out, audio_from=None, workdir=None):
    """Segmentlarni stream-copy bilan birlashtiradi, audio kirishdan copy."""
    lst = os.path.join(workdir or os.path.dirname(segments[0]), "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(f"file '{os.path.basename(s)}'\n")
    cmd = [FFMPEG, "-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", os.path.basename(lst)]
    if audio_from:
        cmd += ["-i", os.path.abspath(audio_from), "-map", "0:v:0", "-map", "1:a:0?", "-c:a", "copy"]
    cmd += ["-c:v", "copy"]
    if out.lower().endswith((".mp4", ".mov")):
        cmd += ["-movflags", "+faststart"]
    cmd += [os.path.abspath(out)]
    subprocess.run(cmd, check=True, cwd=os.path.dirname(lst))


def split_screen(original, result, out, seconds=None):
    cmd = [FFMPEG, "-v", "error", "-nostdin", "-y", "-i", original, "-i", result]
    if seconds:
        cmd += ["-t", str(seconds)]
    enc = ["-c:v", "h264_nvenc", "-cq", "20"] if nvenc_ok() else ["-c:v", "libx264", "-crf", "18"]
    # preview faqat ko'rish uchun: audio AAC (PCM MP4 ichida ko'p playerda ovozsiz)
    cmd += ["-filter_complex", "[0:v][1:v]hstack=shortest=1", "-map", "1:a:0?", "-c:a", "aac", "-b:a", "192k",
            *enc, "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
