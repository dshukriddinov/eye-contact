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
@pytest.mark.parametrize("clip, expected", [("offset.mov", 52), ("offset_both.mov", 0)])
def test_av_offset_preserved(media, tmp_path, monkeypatch, lossless, clip, expected):
    """EC-1: (video - audio) start_time farqi chiqishda saqlanadi (chegara ±1 kadr = 40 ms, amalda ~0).
    offset.mov: video 52 ms kech. offset_both.mov: ikkalasi 80 ms dan, fayl boshi 0 (clip_10s kabi)."""
    stub_maxine.install(monkeypatch, modify=True)
    src = media[clip]
    assert av_offset_ms(src) == pytest.approx(expected, abs=0.5)
    rep = pipeline.run(src, str(tmp_path / ("out.mkv" if lossless else "out.mp4")),
                       pipeline.Config(chunk_sec=4, lossless=lossless, quiet=True))
    got = av_offset_ms(rep["output"])
    assert got == pytest.approx(expected, abs=2)
    from tools import eval as ev
    assert abs(ev.av_offset_ms(video_io.probe(src), video_io.probe(rep["output"]))) < 2


def framemd5(path, vf=None):
    """Kadrlar md5 ro'yxati (yuv420p). vf berilsa butun fayl shu filtr bilan (seek'siz) dekod qilinadi."""
    import subprocess
    cmd = [video_io.FFMPEG, "-v", "error", "-i", path, "-map", "0:v:0"]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-pix_fmt", "yuv420p", "-f", "framemd5", "-"]
    out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=True).stdout
    return [ln.rsplit(",", 1)[1].strip() for ln in out.splitlines() if ln and not ln.startswith("#")]


@pytest.mark.parametrize("chunk_sec", [4, 3.96])  # 3.96 s = 99 kadr: chunk aynan tushgan kadrdan boshlanadi
def test_vfr_matches_ideal_cfr(media, tmp_path, monkeypatch, chunk_sec):
    """EC-2: 6 kadri tushgan VFR (294 kadr, 11.96 s) -> CFR 299 kadr; har kadr butun faylni fps filtri bilan
    o'qilgan ideal CFR ketma-ketlik bilan bir xil (chunk chegarasida siljish yo'q)."""
    stub_maxine.install(monkeypatch, modify=False)
    src = media["vfr.mp4"]
    m = video_io.probe(src)
    assert m["vfr"] and m["nb_frames"] == 299
    ideal = framemd5(src, vf="fps=25")
    assert len(ideal) == 299
    rep = pipeline.run(src, str(tmp_path / "out.mkv"),
                       pipeline.Config(chunk_sec=chunk_sec, lossless=True, quiet=True))
    got = framemd5(rep["output"])
    assert len(got) == 299
    bad = [i for i, (a, b) in enumerate(zip(ideal, got)) if a != b]
    assert not bad, f"farqli kadrlar: {bad[:10]}"
    assert abs(video_io.probe(rep["output"])["duration"] - m["duration"]) * 25 <= 1


def test_resume_ignores_chunks_of_other_file(media, tmp_path, monkeypatch):
    """EC-3: shu nomli boshqa fayl bilan --resume eski chunk'larni ishlatmaydi; o'sha fayl bilan ishlatadi."""
    import shutil
    import subprocess
    stub_maxine.install(monkeypatch, modify=False)
    calls = []
    orig = pipeline.process_chunk
    monkeypatch.setattr(pipeline, "process_chunk", lambda *a, **k: calls.append(a[3]) or orig(*a, **k))
    inp, out, work = str(tmp_path / "dars.mp4"), str(tmp_path / "out.mkv"), str(tmp_path / "work")
    cfg = lambda: pipeline.Config(chunk_sec=4, lossless=True, quiet=True, resume=True, keep_work=True, workdir=work)

    shutil.copy(media["ntsc.mp4"], inp)
    pipeline.run(inp, out, cfg())
    assert len(calls) == 3
    calls.clear()
    pipeline.run(inp, out, cfg())                      # o'sha fayl: hammasi resume
    assert calls == []

    # o'sha nom, o'sha o'lcham/fps/kadr soni, boshqa tarkib
    subprocess.run([video_io.FFMPEG, "-v", "error", "-y", "-i", media["ntsc.mp4"], "-vf", "negate", "-c:a", "copy",
                    inp], check=True)
    pipeline.run(inp, out, cfg())
    assert len(calls) == 3
    assert framemd5(out) == framemd5(inp)


def test_patches_out_equals_full_output(media, tmp_path, monkeypatch):
    """EC-4: --patches-out patchlari kirish kadrlariga qo'llanganda oddiy rejim (lossless) chiqishi bilan bayt-aniq
    (Y va UV); resume ishlaydi; w=0 -> o'zgarishsiz."""
    import json
    import os

    from eyecontact import cli, patches
    stub_maxine.install(monkeypatch, modify=True)
    src, pdir = media["ntsc.mp4"], str(tmp_path / "eyepatch")
    full = pipeline.run(src, str(tmp_path / "full.mkv"), pipeline.Config(chunk_sec=4, lossless=True, quiet=True))
    assert cli.main([src, "--patches-out", pdir, "--chunk-sec", "4", "-q"]) == 0

    with open(os.path.join(pdir, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["format_version"] == patches.FORMAT_VERSION and meta["nb_frames"] == 360
    assert meta["source_id"] == video_io.file_id(src)
    assert [c["file"] for c in meta["chunks"]] == ["chunk_00000.npz", "chunk_00001.npz", "chunk_00002.npz"]
    recs = {r["frame_idx"]: r for c in meta["chunks"] for r in patches.read_chunk(os.path.join(pdir, c["file"]))}
    assert len(recs) == 360

    m = video_io.probe(src)
    w, h = m["width"], m["height"]
    ra = video_io.FrameReader(src, w, h, m["fps"], pix_fmt="yuv420p")
    rb = video_io.FrameReader(full["output"], w, h, m["fps"], pix_fmt="yuv420p")
    for i, (fa, fb) in enumerate(zip(ra, rb)):
        orig = fa.copy()
        assert (patches.apply(fa.copy(), recs[i], w=0.0) == orig).all()
        half = patches.apply(fa.copy(), recs[i], w=0.5)
        assert (half != orig).any() and (half != fb).any()
        assert (patches.apply(fa, recs[i]) == fb).all(), f"kadr {i}"
    assert i == 359

    calls = []
    orig_pc = pipeline.process_chunk
    monkeypatch.setattr(pipeline, "process_chunk", lambda *a, **k: calls.append(1) or orig_pc(*a, **k))
    assert cli.main([src, "--patches-out", pdir, "--chunk-sec", "4", "-q", "--resume"]) == 0
    assert calls == []
