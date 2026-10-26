"""GPU'siz testlar uchun sintetik media (ffmpeg lavfi). Session davomida bir marta yaratiladi."""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eyecontact import video_io  # noqa: E402

# GPU/haqiqiy klip talab qiladigan skriptlar pytest'da yig'ilmaydi (ular to'g'ridan ishga tushiriladi)
collect_ignore = ["test_smoke.py", "test_gui.py"]

S = "640x360"


def _ff(*args):
    subprocess.run([video_io.FFMPEG, "-v", "error", "-nostdin", "-y", *args], check=True,
                   capture_output=True, encoding="utf-8", errors="replace")


def _offset_mov(out):
    # video audiodan 52 ms keyin (Canon MOV kabi, PCM). -itsoffset lavfi'da 1/25 ga yaxlitlanadi, shuning uchun
    # 1/25000 time base'da butun son siljish + -copyts + timescale 25000.
    _ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=25:d=10,settb=1/25000,setpts=PTS+1300",
        "-f", "lavfi", "-i", "sine=f=440:r=48000:d=10", "-map", "0:v", "-map", "1:a",
        "-fps_mode", "passthrough", "-copyts", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-bf", "0",
        "-pix_fmt", "yuv420p", "-enc_time_base:v", "1/25000", "-video_track_timescale", "25000",
        "-movie_timescale", "25000", "-c:a", "pcm_s16le", out)


def _offset_both(out):
    # clip_10s (Canon) kabi: video va audio 80 ms dan boshlanadi, lekin fayl start_time 0 (boshqa stream 0 dan).
    # Bu yerda ikkinchi audio trek 0 dan boshlanadi.
    _ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=25:d=10,settb=1/25000,setpts=PTS+2000",
        "-f", "lavfi", "-i", "sine=f=440:r=48000:d=10,asetpts=PTS+3840",
        "-f", "lavfi", "-i", "sine=f=880:r=48000:d=10", "-map", "0:v", "-map", "1:a", "-map", "2:a",
        "-fps_mode", "passthrough", "-copyts", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-bf", "0",
        "-pix_fmt", "yuv420p", "-enc_time_base:v", "1/25000", "-video_track_timescale", "25000",
        "-movie_timescale", "25000", "-c:a", "pcm_s16le", out)


def _ntsc(out):
    _ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=30000/1001", "-f", "lavfi", "-i", "sine=f=440:r=48000",
        "-frames:v", "360", "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", out)


def _vfr(out):
    # 25 fps manbadan har 50-kadrdan keyin bitta kadr tushirilgan, pts o'zgarmagan: 300 -> 294 kadr
    _ff("-f", "lavfi", "-i", f"testsrc2=s={S}:r=25", "-f", "lavfi", "-i", "sine=f=440:r=48000:d=12",
        "-map", "0:v", "-map", "1:a", "-vf", "select=not(eq(mod(n\\,50)\\,49))", "-frames:v", "294",
        "-fps_mode", "passthrough", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", out)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("media")
    out = {}
    for name, fn in (("offset.mov", _offset_mov), ("offset_both.mov", _offset_both), ("ntsc.mp4", _ntsc), ("vfr.mp4", _vfr)):
        out[name] = str(d / name)
        fn(out[name])
    return out
