"""eyecontact IN OUT [opsiyalar] — uzun talking-head videoda nigohni kameraga qaratish (faqat ko'z hududi)."""
import argparse
import json
import os
import subprocess
import sys
import tempfile

from . import pipeline, video_io


def main(argv=None):
    ap = argparse.ArgumentParser(prog="eyecontact", description=__doc__)
    ap.add_argument("inp", metavar="IN")
    ap.add_argument("out", metavar="OUT", nargs="?", help="natija video (--patches-out bo'lsa kerak emas)")
    ap.add_argument("--chunk-sec", type=int, default=120, help="chunk uzunligi soniyada (default 120)")
    ap.add_argument("--resume", action="store_true", help="mavjud chunk natijalarini qayta ishlamaydi")
    ap.add_argument("--preview", type=float, metavar="SEC", help="faqat birinchi SEC soniya, split-screen chiqish")
    ap.add_argument("--codec", choices=("h264", "hevc"), default="h264")
    ap.add_argument("--bitrate", type=int, metavar="BPS", help="video bitrate; default kirish x1.5; 0 -> --cq")
    ap.add_argument("--cq", type=int, default=18, help="NVENC cq / x264 crf, --bitrate 0 bo'lsa (default 18)")
    ap.add_argument("--lossless", action="store_true", help="FFV1/MKV, eval uchun")
    ap.add_argument("--patches-out", metavar="DIR",
                    help="video o'rniga ko'z patchlarini yozish (Dars Studio uchun): DIR/chunk_XXXXX.npz + meta.json")
    ap.add_argument("--report", metavar="PATH",
                    help="kadr-kadr hisobotni shu faylga yozish (default: hisobot yozilmaydi)")
    ap.add_argument("--workdir", metavar="PATH", help="vaqtinchalik chunk papka (default OUT.work)")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--blend", choices=("lid", "box"), default="lid",
                    help="lid: original qovoq konturi ichida (shakl saqlanadi, default); box: Maxine xom natija")
    ap.add_argument("--lid-open", type=float, default=0.5, metavar="0..1",
                    help="yuqori qovoq qanchalik ochilishi: 0 = original shakl (tuzatish ~35%%), 0.5 = default (~63%%), "
                         "1 = deyarli Maxine xom (~68%%)")
    ap.add_argument("--no-iris-tone", action="store_true", help="iris tonini originalga qaytarishni o'chirish")
    ap.add_argument("--no-upscale", action="store_true",
                    help="kichik yuzni Maxine'ga kattalashtirib berishni o'chirish (tezroq, iris xiraroq)")
    ap.add_argument("--eye-size", type=int, default=2, help="Maxine EyeSizeSensitivity 2-6 (default 2)")
    ap.add_argument("--no-temporal", action="store_true", help="Maxine temporal filtrni o'chirish")
    ap.add_argument("--max-head-yaw", type=float, default=30.0, help="bosh burilishi chegarasi, gradus")
    ap.add_argument("--max-head-pitch", type=float, default=20.0)
    ap.add_argument("--max-gaze", type=float, default=30.0, help="nigoh bundan uzoqda bo'lsa tuzatilmaydi")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--progress", action="store_true", help="UI uchun: 'PROGRESS done total' va 'OUTPUT path' satrlari")
    a = ap.parse_args(argv)
    if not a.out and not a.patches_out:
        ap.error("OUT yoki --patches-out kerak")
    if a.patches_out and a.preview:
        ap.error("--preview va --patches-out birga ishlamaydi")

    cfg = pipeline.Config(chunk_sec=a.chunk_sec, resume=a.resume, codec=a.codec, bitrate=a.bitrate, cq=a.cq,
                          lossless=a.lossless, workdir=a.workdir, patches_out=a.patches_out, keep_work=a.keep_work, eye_size=a.eye_size,
                          blend=a.blend, lid_open=max(0.0, min(1.0, a.lid_open)), upscale=not a.no_upscale,
                          iris_tone=not a.no_iris_tone,
                          on_progress=(lambda d, t: print(f"PROGRESS {d} {t}", file=sys.stderr, flush=True))
                          if a.progress else None,
                          temporal=not a.no_temporal, max_head_yaw=a.max_head_yaw,
                          max_head_pitch=a.max_head_pitch, max_gaze=a.max_gaze, quiet=a.quiet)
    try:
        if a.preview:
            meta = video_io.probe(a.inp)
            n = int(round(a.preview * meta["fps"]))
            tmp = os.path.join(tempfile.gettempdir(), "eyecontact_preview_result.mp4")
            rep = pipeline.run(a.inp, tmp, cfg, max_frames=n)
            video_io.split_screen(a.inp, rep["output"], a.out, seconds=a.preview)
            os.remove(rep["output"])
            rep["output"] = os.path.abspath(a.out)
        else:
            rep = pipeline.run(a.inp, a.out, cfg)
    except (RuntimeError, OSError, SystemExit, subprocess.SubprocessError, ValueError) as e:
        print(f"xato: {e}", file=sys.stderr)
        return 1
    if a.report:  # hisobot faqat so'ralganda (tools/eval.py uchun); natija yonida ortiqcha fayl qolmaydi
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False)
    if not a.quiet:
        print(f"tayyor: {rep['frames_total']} kadr, {rep['frames_changed']} tuzatilgan, "
              f"{rep['frames_skipped']} o'tkazilgan, {rep['seconds']} s ({rep['fps']} fps)"
              + (f". hisobot: {a.report}" if a.report else ""), file=sys.stderr)
    if a.progress:
        print(f"OUTPUT {rep['output']}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
