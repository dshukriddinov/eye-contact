"""Pipeline testlari GPU'siz (EC-5): Maxine o'rniga stub_maxine. Ishga tushirish:
    python -m pytest tests/test_pipeline_stub.py
"""
import hashlib

import pytest
import stub_maxine

from eyecontact import pipeline, video_io


def yuv_md5s(path, count=None):
    """Kadrlar yuv420p baytlarining md5 ro'yxati (rang konvertatsiyasisiz)."""
    m = video_io.probe(path)
    r = video_io.FrameReader(path, m["width"], m["height"], m["fps"], count=count, pix_fmt="yuv420p")
    return [hashlib.md5(f).hexdigest() for f in r]


@pytest.mark.parametrize("clip", ["offset.mov", "ntsc.mp4"])
def test_passthrough_lossless_is_byte_exact(media, tmp_path, monkeypatch, clip):
    """Yuz topilmasa chiqish = kirish (lossless), chunk chegaralarida ham (chunk 4 s -> 3 chunk)."""
    stub_maxine.install(monkeypatch, modify=False)
    rep = pipeline.run(media[clip], str(tmp_path / "out.mkv"), pipeline.Config(chunk_sec=4, lossless=True,
                                                                              quiet=True))
    assert rep["frames_changed"] == 0
    assert yuv_md5s(rep["output"]) == yuv_md5s(media[clip])


def test_modify_stub_changes_only_eye_box(media, tmp_path, monkeypatch):
    """Patch yo'li GPU'siz ishlaydi: har kadr o'zgaradi, o'zgarish faqat diff box ichida."""
    stub_maxine.install(monkeypatch, modify=True)
    rep = pipeline.run(media["ntsc.mp4"], str(tmp_path / "out.mkv"),
                       pipeline.Config(chunk_sec=4, lossless=True, quiet=True))
    assert rep["frames_changed"] == rep["frames_total"] == 360
    m = video_io.probe(media["ntsc.mp4"])
    w, h = m["width"], m["height"]
    ra = video_io.FrameReader(media["ntsc.mp4"], w, h, m["fps"], pix_fmt="yuv420p")
    rb = video_io.FrameReader(rep["output"], w, h, m["fps"], pix_fmt="yuv420p")
    for i, (fa, fb) in enumerate(zip(ra, rb)):
        x0, y0, x1, y1 = rep["per_frame"]["box"][i]
        ya, yb = fa[: w * h].reshape(h, w).copy(), fb[: w * h].reshape(h, w).copy()
        assert (ya != yb).any(), i
        ya[y0:y1, x0:x1] = yb[y0:y1, x0:x1] = 0
        assert (ya == yb).all(), f"kadr {i}: box tashqarisi o'zgargan"
    assert i == 359


def av_offset_ms(path):
    """video start_time - audio start_time, ms."""
    m = video_io.probe(path)
    return (m["start_time"] - m["audio_start_time"]) * 1000


@pytest.mark.parametrize("lossless", [True, False])
def test_av_offset_preserved(media, tmp_path, monkeypatch, lossless):
    """EC-1: kirishda video audiodan 52 ms keyin boshlanadi -> chiqishda ham (±1 kadr = 40 ms, amalda ~0)."""
    stub_maxine.install(monkeypatch, modify=True)
    src = media["offset.mov"]
    assert av_offset_ms(src) == pytest.approx(52, abs=0.5)
    rep = pipeline.run(src, str(tmp_path / ("out.mkv" if lossless else "out.mp4")),
                       pipeline.Config(chunk_sec=4, lossless=lossless, quiet=True))
    got = av_offset_ms(rep["output"])
    assert got == pytest.approx(52, abs=2)
    from tools import eval as ev
    assert abs(ev.av_offset_ms(video_io.probe(src), video_io.probe(rep["output"]))) < 2
