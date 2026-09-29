# Texnik topshiriq: Eye Contact (uzun videolar uchun nigoh tuzatish)

Versiya: 1.0
Sana: 2026-09-18
Holat: qoralama

---

## 1. Maqsad

Talking-head formatdagi 20-25 minutlik videolarda so'zlovchining nigohini kameraga qaratib beradigan offline dastur. Faqat ko'z hududi o'zgaradi. Yuz shakli, teri, qosh, burun, og'iz, soch, fon piksel darajasida o'zgarmaydi.

## 2. Muammo

So'zlovchi matnni ekrandan yoki qog'ozdan o'qiydi, nigoh kameradan 5-20° pastga yoki yonga og'gan. Tomoshabinga "ko'zga qaramayapti" tuyuladi. Mavjud yechimlar (Descript, Captions) bulutda, pullik, real-time yoki qisqa klipga mo'ljallangan. Uzun videoda yuz "suzib ketishi" (identity drift) va ko'z titrashi (flicker) kuzatiladi.

## 3. Qamrov

Kiradi:
- Lokal MP4/MOV fayl kirish, MP4 fayl chiqish
- Bitta asosiy so'zlovchi (kadrda eng katta yuz)
- 1080p va 4K, 24-60 fps
- Windows 11, bitta RTX GPU

Kirmaydi:
- Real-time / webcam rejim
- Bir nechta yuzni bir vaqtda tuzatish
- Bosh burilishini tuzatish (faqat ko'z, bosh emas)
- GUI (faqat CLI)

## 4. Funksional talablar

| ID | Talab |
|----|-------|
| FR-1 | CLI: `eyecontact <in.mp4> <out.mp4> [opsiyalar]` |
| FR-2 | Chiqish: kirish bilan bir xil rezolyutsiya, fps, davomiylik (kadr soni teng) |
| FR-3 | Audio o'zgarmaydi: stream copy, qayta kodlanmaydi |
| FR-4 | Har kadr uchun ko'z nigohi kameraga (yaw 0°, pitch 0°) yo'naltiriladi |
| FR-5 | Faqat ko'z maskasi ichidagi piksellar o'zgaradi (qarang 6-bo'lim) |
| FR-6 | Ko'z yumuq kadrlar (blink) o'zgartirilmaydi |
| FR-7 | Nigoh allaqachon kameraga (chegara ichida) bo'lsa kadr o'zgartirilmaydi |
| FR-8 | Bosh burilishi chegaradan oshsa kadr o'zgartirilmaydi |
| FR-9 | Yuz topilmagan kadr o'zgartirilmaydi |
| FR-10 | Chunk asosida ishlash, `--resume` bilan uzilgan joydan davom etish |
| FR-11 | Har run oxirida JSON hisobot: qayta ishlangan/skip qilingan kadrlar soni, sabablari, metrikalar |
| FR-12 | `--preview N` opsiyasi: faqat birinchi N soniyani ishlab, split-screen (original / natija) chiqarish |

## 5. Nofunksional talablar

| ID | Talab | Qiymat |
|----|-------|--------|
| NFR-1 | Tezlik (RTX 5070 Ti, 1080p30, 25 min) | ≤ 10 min |
| NFR-2 | Tezlik (4K30, 25 min) | ≤ 30 min |
| NFR-3 | VRAM | ≤ 12 GB |
| NFR-4 | RAM | ≤ 48 GB (chunk xotirada) |
| NFR-5 | Disk vaqtinchalik | ≤ 2 × kirish fayl hajmi |
| NFR-6 | Deterministik | Bir xil kirish + config = bit-identical chiqish |
| NFR-7 | Crash bo'lsa ma'lumot yo'qolmaydi | Chunk checkpoint |

## 6. Yuz shaklini saqlash talablari (asosiy)

Bu bo'lim loyihaning mohiyati. Har biri qabul testida tekshiriladi.

**IP-1. Mask chegarasi.** O'zgartirish maskasi = ko'z olmasi + qovoqlar. Landmark asosida (MediaPipe Face Mesh ko'z konturi: chap ko'z 33/133/159/145, o'ng ko'z 362/263/386/374 va qo'shni nuqtalar). Maksimal dilatsiya: ko'z kengligining 15%. Feather: 3-6 px (1080p da), rezolyutsiyaga proporsional.

**IP-2. Mask tashqarisi piksel-identik.** Har kadrda mask tashqarisidagi piksellar kirish kadri bilan bayt darajasida teng. Test dekodlangan kadrlar ustida, enkodgacha o'tkaziladi (enkod yo'qotishi hisobga olinmaydi).

**IP-3. Full-face generativ model taqiqlanadi.** Face swap, full-face GAN, butun yuzga diffusion inpainting ishlatilmaydi. Faqat ko'z patch ustida warp/flow yoki lokal generativ model.

**IP-4. Identity metrikasi.** ArcFace (InsightFace `buffalo_l`) embedding: original kadr vs natija kadr cosine similarity. Median ≥ 0.97, minimum ≥ 0.93 (qayta ishlangan kadrlar ichida).

**IP-5. Ko'z geometriyasi.** Ko'z ochiqlik darajasi (EAR, eye aspect ratio) natijada originaldan ±10% dan ortiq farq qilmaydi. Ko'z kattalashmaydi, kichraymaydi.

**IP-6. Blink saqlanadi.** Blink soni (EAR < 0.2 epizodlar) original va natijada ±5% ichida.

**IP-7. Aralashmaslik siyosati.** Shubha bo'lsa o'zgartirma. Skip shartlari:
- EAR < 0.20 (blink)
- |gaze yaw| ≤ 5° va |gaze pitch| ≤ 5° (allaqachon kameraga)
- |head yaw| > 30° yoki |head pitch| > 20°
- Yuz bounding box balandligi < kadr balandligining 8% (juda kichik)
- Landmark confidence < 0.7
- Ko'z patch ustida okklyuziya (qo'l, soch): landmark visibility < 0.5

**IP-8. Temporal barqarorlik.**
- Gaze vektor va ko'z landmarklariga EMA (exponential moving average), alpha = 0.3 (config)
- Gisterezis: skip/process holat kamida 6 kadr ushlab turiladi, har kadrda o'tib-qaytmaydi
- Flicker metrikasi: ketma-ket natija kadrlari ko'z patchi o'rtasidagi mean abs diff ≤ 1.5 × kirishdagi shu qiymat

## 7. Arxitektura

Ikki variant. A asosiy, B zaxira. A yetarli bo'lsa B qurilmaydi.

### 7.1 Variant A: NVIDIA Maxine AR SDK (asosiy)

Nima uchun: tayyor, bepul (MIT kod + bepul redistributable), RTX 50 qo'llaydi, ko'z hududini warp qiladi, full-face emas.

Komponentlar:
- `Maxine-AR-SDK` (GitHub, MIT) + `AR SDK v0.8.7` redistributable installer
- `AR-SDK-Samples/GazeRedirectionApp` (C++, CMake, VS2022)
- Python wrapper: chunk, resume, skip mantiq (IP-7), hisobot, eval

Oqim:
```
in.mp4 -> ffmpeg chunk (120s) -> GazeRedirectionApp har chunk -> eval har chunk
       -> ffmpeg concat + audio copy -> out.mp4 + report.json
```

Cheklovlar:
- Maxine ichki skip mantig'i sozlanmasa, IP-7 tashqaridan ta'minlanadi: chunk oldidan landmark tahlil, skip kadrlar ro'yxati, Maxine natijasidan keyin shu kadrlar originalga qaytariladi (frame-level replace)
- Maxine SDK faqat Windows/Linux + RTX, Docker yo'q

### 7.2 Variant B: o'z pipeline (zaxira)

Faqat A qabul testidan o'tmasa quriladi.

```
in.mp4
  -> decode (PyAV / ffmpeg pipe, NVDEC)                    [video_io]
  -> face detect + 468 landmark (MediaPipe Face Mesh)      [face]
  -> head pose (solvePnP), EAR, gaze estimate (L2CS-Net)   [face, gaze]
  -> skip qarori (IP-7) + gisterezis                       [smooth]
  -> ko'z patch crop + normalizatsiya (ETH-XGaze usuli)    [gaze]
  -> redirect model (STED yoki ReDirTrans), target (0,0)   [gaze]
  -> mask (IP-1) + feather + cv2.seamlessClone             [blend]
  -> encode (NVENC h264/hevc), audio copy                  [video_io]
  -> report.json                                           [pipeline]
```

Model tanlovi (tartib bilan sinash):
1. STED (Zheng et al. 2020, ETH-XGaze) — warp asosida, identity saqlaydi, ochiq kod
2. ReDirTrans — transformer, sifat yuqori, og'irroq
3. Kerak bo'lsa patch super-resolution (4K uchun) — Real-ESRGAN x2 faqat patchga

Tezlik uchun:
- Landmark har 2-kadrda, oraliqda optical flow (`cv2.calcOpticalFlowPyrLK`) bilan interpolyatsiya
- Redirect batch 128 patch
- Decode/encode alohida threadlarda, GPU navbati to'la turadi

## 8. Kirish/chiqish

Kirish:
- Konteyner: MP4, MOV, MKV
- Kodek: H.264, H.265, ProRes
- Rezolyutsiya: 720p dan 4K gacha
- FPS: 23.976 dan 60 gacha. O'zgaruvchan fps (VFR) bo'lsa avval CFR ga konvert, ogohlantirish

Chiqish:
- MP4, H.264 (default) yoki H.265 (`--codec hevc`), NVENC, `-cq 18` (config)
- `--lossless` opsiyasi: FFV1/MKV, eval uchun
- Audio: `-c:a copy`
- Metadata: rotation, color space saqlanadi

## 9. CLI

```
eyecontact IN OUT
  --engine {maxine,custom}       default: maxine
  --chunk-sec INT                default: 120
  --resume                       mavjud chunk natijalarini qayta ishlamaydi
  --preview SEC                  faqat birinchi SEC soniya, split-screen chiqish
  --gaze-threshold DEG           default: 5
  --ear-threshold FLOAT          default: 0.20
  --max-head-yaw DEG             default: 30
  --max-head-pitch DEG           default: 20
  --smooth FLOAT                 EMA alpha, default: 0.3
  --hold-frames INT              gisterezis, default: 6
  --codec {h264,hevc}            default: h264
  --cq INT                       NVENC sifat, default: 18
  --lossless
  --strict                       qabul metrikasi o'tmasa exit 2
  --report PATH                  default: OUT.report.json
  --workdir PATH                 vaqtinchalik chunk papka
  --gpu INT                      default: 0
  -v / -q
```

Chiqish kodi: 0 muvaffaqiyat, 1 xato, 2 qabul metrikasi o'tmadi (`--strict` bilan).

## 10. Baholash vositasi (`tools/eval.py`)

Kirish: original.mp4, natija.mp4, report.json. Chiqish: metrics.json + PASS/FAIL.

| Metrika | Usul | Chegara |
|---------|------|---------|
| mask_leak | Mask tashqarisi MSE, dekodlangan kadrlar, lossless rejimda | == 0 |
| identity_median / identity_min | ArcFace cosine, original vs natija | ≥ 0.97 / ≥ 0.93 |
| ear_drift | abs(EAR_out - EAR_in) / EAR_in, median | ≤ 0.10 |
| blink_count_ratio | blink_out / blink_in | 0.95 - 1.05 |
| gaze_success | Mustaqil gaze estimator (L2CS-Net) natija ustida, abs(yaw) va abs(pitch) ≤ 5° ulushi, qayta ishlangan kadrlar ichida | ≥ 0.90 |
| flicker_ratio | ko'z patch ketma-ket diff, natija / kirish | ≤ 1.5 |
| frame_count | kadr soni | teng |
| duration_diff | davomiylik farqi | ≤ 1 kadr |
| audio_hash | audio stream md5 | teng |

Sub'ektiv test: 5 kishi, 10 ta 30-soniyalik juftlik (original/natija, tasodifiy tartib). Savollar: "yuz o'zgarganmi?" va "ko'z tabiiymi?". Maqsad: "yuz o'zgargan" ≤ 10%, "ko'z tabiiy" ≥ 80%.

## 11. Muhit

Apparat (mavjud):
- CPU i7-14700K (20 yadro), RAM 64 GB, GPU RTX 5070 Ti 16 GB (Blackwell, sm_120)

Dasturiy:
- Windows 11, NVIDIA driver ≥ 570 (Blackwell)
- Variant A: Visual Studio 2022, CMake ≥ 3.20, AR SDK v0.8.7
- Variant B: Python 3.11, PyTorch ≥ 2.7 `cu128` wheel (eski wheel Blackwell ni tanimaydi), CUDA 12.8, OpenCV, MediaPipe, InsightFace (onnxruntime-gpu), PyAV, ffmpeg ≥ 7 (NVENC/NVDEC bilan)

## 12. Loyiha tuzilishi

```
eye contact/
  TEXNIK_TOPSHIRIQ.md
  README.md
  requirements.txt
  eyecontact/
    cli.py          argparse, engine tanlash
    video_io.py     probe, chunk, decode/encode, concat, audio copy
    face.py         detect, landmark, EAR, head pose, skip qarori
    smooth.py       EMA, gisterezis
    gaze.py         gaze estimate, patch crop/normalize, redirect (B)
    blend.py        mask, feather, seamlessClone (B)
    maxine.py       GazeRedirectionApp wrapper (A)
    pipeline.py     orkestratsiya, checkpoint, report
  tools/
    eval.py         10-bo'lim metrikalari
    make_preview.py split-screen
  tests/
    clip_10s.mp4    test klip
    test_smoke.py   10s klip end-to-end: mask_leak == 0, frame_count teng
```

Bitta smoke test yetadi. Har funksiyaga alohida test yozilmaydi.

## 13. Ish rejasi

| Bosqich | Ish | Muddat | Natija |
|---------|-----|--------|--------|
| M0 | SDK o'rnatish, GazeRedirectionApp build, 1 min klip | 1-2 kun | Ishlaydigan binary, split-screen preview |
| M1 | `eval.py` (10-bo'lim), lossless rejimda 1 min klip baholash | 2-3 kun | metrics.json |
| M2 | Qaror nuqtasi: A o'tdimi? | 0 | Ha: M3-A. Yo'q: M3-B |
| M3-A | Wrapper: chunk, resume, skip post-filter, report, 25 min full run | 3-4 kun | v1.0 |
| M3-B | Pipeline skeleti: decode, landmark, skip, blend (redirect = identity), mask_leak == 0 | 1 hafta | Skeleton |
| M4-B | STED integratsiya, temporal, tuning, 1 min eval | 1 hafta | Sifat |
| M5-B | 25 min full run, tezlik optimizatsiya, NFR tekshiruv | 3-5 kun | v1.0 |

## 14. Xavflar

| Xavf | Ehtimol | Chora |
|------|---------|-------|
| Maxine v0.8.7 RTX 50 da driver xatosi | O'rta | Driver yangilash, NVIDIA forum, B ga o'tish |
| Maxine skip mantig'i sozlanmaydi, blink buziladi | O'rta | Tashqi frame-level replace (7.1) |
| Ochiq redirect modellar 64x32 patchda o'qitilgan, 4K da blur | Yuqori (B) | Patch SR, yoki 1080p da ishlab 4K ga blend |
| Ko'zoynak aksi, qalin ko'zoynak | O'rta | Okklyuziya skip, sub'ektiv testda ko'zoynakli klip |
| PyTorch/Blackwell mos kelmasligi | Past | cu128 wheel, 11-bo'lim |
| VFR video kadr soni mos kelmaydi | Past | Avval CFR ga konvert |

## 15. Qabul mezonlari (v1.0)

1. 10-bo'lim barcha metrikalari PASS, 3 xil test video ustida: 1080p30 25 min, 4K30 20 min, ko'zoynakli 1080p 5 min
2. NFR-1, NFR-2 bajarilgan
3. `--resume` crash simulyatsiyasida (chunk o'rtasida kill) to'g'ri davom etadi, chiqish bit-identical
4. Sub'ektiv test chegaralari (10-bo'lim) bajarilgan
5. README: o'rnatish, ishga tushirish, eval, 1 sahifa

## 16. Ochiq savollar

- Kirish videolarda so'zlovchi doim bitta va markazdami? (Ha deb qabul qilinadi)
- Ko'zoynak kiyadigan so'zlovchilar ulushi? (Test klip kerak)
- Chiqish kodek talabi: platforma (YouTube/Telegram) H.264 talab qiladimi? (Default H.264)
