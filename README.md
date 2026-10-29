# Eye Contact — uzun videolarda nigohni kameraga qaratish

Talking-head videoda (20-25 min) so'zlovchining nigohini kameraga qaratadi. Faqat ko'z olmasi va yuqori qovoq
o'zgaradi: yuz, fon, audio piksel/bayt darajasida original qoladi. Engine: NVIDIA Maxine AR SDK (GazeRedirection).

**Portativ paket.** Papkani istalgan kompyuterga nusxalab (USB, tarmoq) ishga tushirasiz. Python, ffmpeg va Maxine SDK
`runtime\` ichida. O'rnatish, administrator ruxsati, internet kerak emas.

## Ishlatish

1. `EyeContact.bat` ni ikki marta bosing. (Ish stoliga yorliq kerak bo'lsa: `Ish_stoliga_yorliq.bat`.)
2. Dastur ochilganda GPU, drayver va SDK ni tekshiradi, jurnalda «Tekshiruv OK» chiqadi.
3. «Video qo'shish…» bilan bir yoki bir nechta video tanlang, «Boshlash» ni bosing. Navbat bilan ishlanadi.
4. Natija video yonida `<nom>_eyecontact.mp4` (kamera audiosi PCM bo'lsa `.mov`). «Natija papkasini ochish» faylni ko'rsatadi.

- «Preview (30 s, yonma-yon)»: birinchi 30 soniya, chapda original, o'ngda natija. Tayyor bo'lgach o'zi ochiladi.
- «To'xtatish»: keyin «Boshlash» bosilsa uzilgan joydan davom etadi (sozlama o'zgarmagan bo'lsa).
- «Tuzatish kuchi»: 0.5 tavsiya etilgan. 0 = ko'z shakli qat'iy saqlanadi, tuzatish sust; 1 = eng kuchli, ko'z ochiqroq.
- Tezlik: 1080p da 62-70 kadr/s (RTX 5070 Ti), 25 minutlik 1080p25 video 9-10 daqiqa.

## Talablar

- Windows 10/11, NVIDIA RTX video karta, NVIDIA drayver 570 yoki yangiroq (nvidia.com/drivers).
- Paketdagi Maxine SDK **RTX 50 seriya (Blackwell)** uchun. RTX 40/30/20 bo'lsa dastur ishga tushganda buni aytadi;
  `SDK_ornatish.bat` ni bir marta ishga tushiring (GPU ga mos SDK ni yuklaydi, ~1.3 GB, internet va administrator).
  Keyin dastur tizimdagi SDK ni o'zi topadi.
- Kirish video: MP4/MOV/MKV, H.264/H.265/ProRes, 8-bit 4:2:0 (yuv420p). 10-bit/HDR qo'llanmaydi. Bitta yuz (eng katta).

## Paket tarkibi

```
EyeContact.bat            ishga tushirish
Ish_stoliga_yorliq.bat    ish stoliga yorliq
SDK_ornatish.bat/.ps1     faqat RTX 40/30/20 uchun (SDK yuklash)
eyecontact/               dastur: gui.py (UI), cli.py, pipeline.py, maxine.py (SDK ctypes), video_io.py (ffmpeg),
                          theme.py (dizayn tokenlari), widgets.py (UI komponentlari)
design-system/            UI dizayn tizimi: README.md, tokens.json, components/ (UI shu tizim bo'yicha qurilgan)
assets/eyecontact.ico     logotip (tools/make_icon.py bilan qayta yasaladi)
runtime/python/           Python 3.11 + numpy + opencv (portativ)
runtime/ffmpeg/           ffmpeg 7.1.1, ffprobe
runtime/maxine/           Maxine AR SDK v0.8.7 (Blackwell): DLL + gaze/face modellari, ARCH.txt
tests/                    test_smoke.py, test_gui.py, clip_10s.mp4
tools/eval.py             sifat metrikalari (dasturchi uchun, requirements-eval.txt + models/)
```

## GitHub'dan olganda

Repozitoriyda faqat kod va hujjatlar bor. `runtime/` (Python, ffmpeg, Maxine SDK, ~1.9 GB) va test klip hajmi katta
bo'lgani uchun kiritilmagan. Ikki yo'l:

- **Tayyor paketdan:** portativ papkadagi `runtime/` ni repo yoniga nusxalang, keyin `EyeContact.bat`.
- **Qo'lda:** Python 3.11 (`pip install -r requirements.txt`), ffmpeg 7.1.1 (`winget install Gyan.FFmpeg -v 7.1.1`) va
  Maxine AR SDK (`SDK_ornatish.bat`). Dastur ffmpeg ni PATH dan, SDK ni Program Files dagi standart joydan ham topadi.
  Bu holda `python -m eyecontact.gui` bilan ishga tushiriladi.

Testlar uchun `tests/clip_10s.mp4` kerak: 1080p, 25 kadr/s, 10 soniya (250 kadr), kadrda bitta yuz, 8-bit 4:2:0.

## Buyruq qatori

```
runtime\python\python.exe -m eyecontact.cli IN.mov OUT.mp4
runtime\python\python.exe -m eyecontact.cli IN.mov preview.mp4 --preview 30
runtime\python\python.exe -m eyecontact.cli IN.mov OUT.mp4 --resume
runtime\python\python.exe -m eyecontact.cli IN.mov OUT.mkv --lossless      # eval uchun (FFV1)
runtime\python\python.exe -m eyecontact.cli --help
```

| Opsiya | Default | Ma'no |
|--------|---------|-------|
| `--lid-open 0..1` | 0.5 | yuqori qovoq qanchalik ochilishi. Test videoda (og'ish 7.7°): 0 -> tuzatish 35%, ko'z ochiqligi +7%; 0.5 -> 63%, +13%; `--blend box` -> 68%, +15% |
| `--blend lid\|box` | lid | box: Maxine xom natija (ko'z kattalashadi) |
| `--no-iris-tone` | yoqilgan | Maxine kulrang chizgan irisni original toniga qaytarishni o'chirish |
| `--no-upscale` | yoqilgan | kichik yuzni Maxine'ga 2-4x kattalashtirib berishni o'chirish (tezroq, iris xiraroq) |
| `--bitrate BPS` | kirish x1.5 | 0 bo'lsa `--cq` (NVENC cq / x264 crf, default 18) |
| `--codec h264\|hevc` | h264 | DaVinci Resolve bepul versiyasi Windows'da HEVC ochmaydi |
| `--chunk-sec` | 120 | chunk uzunligi; har chunk segment + JSON (checkpoint, resume) |
| `--max-head-yaw/-pitch`, `--max-gaze` | 30/20/30 | bundan tashqarida Maxine tuzatmaydi (gisterezis) |
| `--patches-out DIR` | — | video o'rniga ko'z patchlari (Dars Studio uchun): `DIR/chunk_XXXXX.npz` + `meta.json`, OUT kerak emas |

Chiqish: video qayta kodlangan (NVENC, bo'lmasa CPU x264), audio `-c:a copy` (bayt-aniq), rang teglari saqlanadi,
natija yonida ortiqcha fayl qoldirilmaydi. PCM audio MP4 ichida ko'p playerda ovozsiz, shuning uchun `.mov`.
Kadr-kadr hisobot kerak bo'lsa (gaze/head/conf/box): `--report OUT.report.json`.

## Qanday ishlaydi

```
ffmpeg decode (bgr24) ─► yuz crop 2-4x ─► Maxine ─► delta ─► qovoq maskasi + iris toni ─► BGR→YUV patch ─┐
ffmpeg decode (yuv420p, xom baytlar) ───────────────────────────────────────────────────────────────────┴► NVENC ─► segment
segmentlar ─► ffmpeg concat (-c copy) + audio copy ─► OUT
```

Chiqish kadri = kirishning yuv420p baytlari, faqat Maxine haqiqatan o'zgartirgan piksellar yoziladi (kadrda ~1 100 ta,
ko'z atrofida). Qolgan hamma piksel bayt-aniq (lossless rejimda `mask_leak == 0`). Chunk boshida 25 kadr warm-up. Muhit o'zgaruvchisi `NVAR_SDK_DIR` SDK papkasini majburlaydi.

Tekshirish: `runtime\python\python.exe tests\test_smoke.py` (10 s klip, 3 chunk, mask_leak == 0, audio teng),
`runtime\python\python.exe tests\test_gui.py` (UI odamsiz).
GPU va haqiqiy klipsiz (Linux'da ham): `python -m pytest tests/test_pipeline_stub.py` (Maxine o'rniga stub, sintetik
media: bayt-aniqlik, A/V siljish, VFR, resume kaliti, patch fayli). Kerak: `pip install pytest` + `requirements.txt`.

Yangilashda: `requirements.txt` ga `xxhash` qo'shildi. Mavjud portativ paketda bir marta:
`runtime\python\python.exe -m pip install xxhash`.

## Muammo chiqsa

Oynadagi jurnal `logs\gui.log` fayliga ham yoziladi (oxirgi 2 MB). Xato bo'lsa shu fayldagi oxirgi satrlarni qarang:
ularda to'liq sabab bor. Masalan "ffprobe videoni o'qiy olmadi" degan xato fayl hali yozilayotgan, band yoki
formati qo'llanmaydigan bo'lsa chiqadi.

## Cheklovlar

- 10-bit/HDR yo'q. Bosh 30°/20° dan ko'p burilsa yoki ko'z yumuq bo'lsa Maxine tuzatmaydi (original qoladi).
- Maxine chegarasi: og'ishning ~68% tuzatiladi (kuch 1 da). Pastga tushgan qovoqning o'zi "pastga qarayapti" belgisi.
- Determinizm: qarorlar bir xil, piksellar GPU inference tufayli ±1 farq qilishi mumkin.
