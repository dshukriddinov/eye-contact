# Texnik topshiriq: Eye Contact — uzun videolarda nigohni kameraga qaratish

| | |
|---|---|
| Versiya | 2.0 — bajarilgan ish holati |
| Sana | 2026-09-22 |
| Holat | Ishlaydigan portativ dastur (UI va buyruq qatori). 1080p25 videoda, RTX 5070 Ti da sinovdan o'tgan |
| Oldingi versiya | `TEXNIK_TOPSHIRIQ_v1.0.md` — dastlabki talablar (2026-09-18) |

Bu hujjat v1.0 talablari qanday bajarilganini, o'lchangan natijalarni, ish davomida qabul qilingan qarorlarni va
ochiq qolgan masalalarni qayd etadi. Bo'limlar raqami v1.0 bilan bir xil, ikkala hujjatni yonma-yon solishtirish mumkin.

## Qisqacha

- **Nima qiladi.** Talking-head videoda so'zlovchining nigohini kameraga qaratadi. Faqat ko'z olmasi va yuqori qovoq
  o'zgaradi. Kadrning qolgan qismi kodlashdan oldin kirish bilan bayt darajasida bir xil, audio qayta kodlanmaydi.
- **Engine.** NVIDIA Maxine AR SDK v0.8.7 (GazeRedirection), Python `ctypes` orqali chaqiriladi.
- **Ishga tushirish.** `EyeContact.bat`. Python, ffmpeg va Maxine SDK paket ichida (`runtime\`), hech narsa o'rnatilmaydi.
- **Sifat.** 13 minutlik test videoda barcha qabul metrikalari o'tdi: identity 0.993, ko'z ochiqligi farqi 10.9%,
  blink nisbati 1.01, flicker nisbati 1.01, kadr soni va audio teng. Qayta kodlash yo'qotishi: VMAF 97.8.
- **Tuzatish kuchi.** Kameradan og'ish 7.7° dan 2.8° ga tushadi, ya'ni taxminan 63%.
- **Tezlik.** 1080p da 62-70 kadr/s: 25 minutlik 1080p25 video 9-10 daqiqada.
- **Ochiq.** Sub'ektiv test, 4K va 25 minutlik videolarda sinov, RTX 40/30/20 kartalarda sinov (16-bo'lim).

---

## 1. Maqsad

Talking-head formatdagi 20-25 minutlik videolarda so'zlovchining nigohini kameraga qaratib beradigan offline dastur.
Faqat ko'z hududi o'zgaradi. Yuz shakli, teri, qosh, burun, og'iz, soch va fon o'zgarmaydi, video sifati sezilarli
pasaymaydi.

**Holat:** bajarildi. Cheklovlar 10 va 16-bo'limlarda.

## 2. Muammo va boshlang'ich holat

So'zlovchi matnni ekrandan yoki qog'ozdan o'qiydi, nigoh kameradan pastga yoki yonga og'gan. Tomoshabinga
"ko'zga qaramayapti" tuyuladi. Mavjud yechimlar bulutda, pullik yoki qisqa kliplarga mo'ljallangan.

### 2.1 Test video

| Parametr | Qiymat |
|---|---|
| Fayl | `DSBA8944.MOV`, Canon EOS 5D Mark III |
| Video | H.264 High, 1920×1080, 25 kadr/s, yuvj420p (to'liq diapazon), BT.709, 22.7 Mbit/s |
| Audio | PCM s16le, 48 kHz, stereo |
| Davomiylik | 13 min 19 s (799.4 s), 19 985 kadr, 2.4 GB |
| Mazmun | So'zlovchi ko'zoynakli, yashil fon, matnni o'qiydi |
| Yuz o'lchami | Balandligi ~230 px (kadrning 21%), bitta ko'z kengligi ~24 px |
| Boshlang'ich nigoh | Kameradan 7.7-7.8° og'gan: taxminan 6° pastga, 4° yonga |

Nigoh Maxine estimatori bilan, ko'zlar markazda turgan 3× kattalashtirilgan crop ustida o'lchangan (10.5-bo'lim).
Dastlabki "20° pastga" o'qishi noto'g'ri bo'lgan: Maxine burchakni rasm markaziga nisbatan o'lchaydi, to'liq kadrda esa
ko'zlar markazdan 325 px yuqorida joylashgan.

### 2.2 Uchinchi tomon vositasi bilan taqqoslash

Foydalanuvchida shu videoning boshqa vosita bilan ishlangan nusxasi bor edi (`DSBA8944_eye.mp4`).

| Ko'rsatkich | Uchinchi tomon vositasi | Eye Contact v2.0 |
|---|---|---|
| Qolgan og'ish | 1.3° (84% tuzatish) | 2.8° (63% tuzatish) |
| Ko'z ochiqligi (EAR) | +19%, ko'z sezilarli kattalashgan | +13%, faqat yuqori qovoq ko'tariladi |
| Ko'zoynakdagi aks | o'chirilgan | saqlangan |
| Audio | AAC ga qayta kodlangan | bayt-aniq nusxa (PCM) |
| Rang teglari | yo'qolgan | saqlangan |
| Video bitrate | 15.0 Mbit/s | ~28 Mbit/s |

Uchinchi tomon vositasi nigohni kuchliroq tuzatadi, lekin v1.0 aynan oldini olmoqchi bo'lgan yuz shakli o'zgarishini
beradi.

## 3. Qamrov

Kiradi:
- Lokal video fayl kirish: MP4, MOV, MKV. Chiqish MP4; audio PCM bo'lsa MOV; lossless rejimda MKV.
- Bitta asosiy so'zlovchi (kadrdagi eng katta yuz).
- 8-bit 4:2:0 video (yuv420p, yuvj420p), 24-60 kadr/s. Dastur 720p-4K ni qabul qiladi, sinovdan o'tgani faqat 1080p25.
- Windows 10/11, bitta NVIDIA RTX GPU.
- Grafik interfeys (UI). v1.0 da qamrovdan tashqari edi, foydalanuvchi so'rovi bilan qo'shildi.
- Portativ paket: papkani nusxalab ishga tushirish.

Kirmaydi:
- Real-time yoki webcam rejimi.
- Bir nechta yuzni bir vaqtda tuzatish.
- Bosh burilishini tuzatish.
- 10-bit, HDR (PQ, HLG), 4:2:2 va 4:4:4 video. Dastur xato bilan to'xtaydi.
- macOS, Linux, AMD va Intel GPU.

## 4. Funksional talablar

| ID | Talab | Holat | Qanday bajarilgan |
|----|-------|-------|-------------------|
| FR-1 | Buyruq qatori | Bajarildi | `runtime\python\python.exe -m eyecontact.cli IN OUT [opsiyalar]` (9.2-bo'lim) |
| FR-2 | Rezolyutsiya, fps, davomiylik, kadr soni teng | Bajarildi | Har chunkda kadr soni tekshiriladi, mos kelmasa xato. Smoke test va eval tekshiradi |
| FR-3 | Audio o'zgarmaydi | Bajarildi | `-c:a copy`, md5 teng. PCM audio bo'lsa konteyner `.mov` (14-bo'lim, 5-band) |
| FR-4 | Nigoh kameraga yo'naltiriladi | Bajarildi | Maxine GazeRedirection, og'ishning ~63% tuzatiladi (10.4-bo'lim) |
| FR-5 | Faqat ko'z maskasi ichidagi piksellar o'zgaradi | Bajarildi | O'zgargan piksellargina yoziladi, qolgani kirish baytlari (IP-2) |
| FR-6 | Ko'z yumuq kadrlar o'zgartirilmaydi | Bajarildi | Maxine `DetectClosure` (default yoqilgan). Blink nisbati 1.01 |
| FR-7 | Nigoh allaqachon kameraga bo'lsa o'zgartirilmaydi | Qisman | Tashqi qoida qurilmadi. Maxine nigoh kameraga yaqin bo'lsa kichik o'zgarish beradi; tashqi o'chirish-yoqish chegarada "sakrash" beradi |
| FR-8 | Bosh burilishi chegaradan oshsa o'zgartirilmaydi | Bajarildi | Maxine ichki gisterezisi: yaw 25/30°, pitch 15/20° (`--max-head-yaw`, `--max-head-pitch`) |
| FR-9 | Yuz topilmagan kadr o'zgartirilmaydi | Bajarildi | Landmark ishonchliligi < 0.15 bo'lsa kadr original qoladi, hisobotda sababi yoziladi |
| FR-10 | Chunk asosida ishlash, `--resume` | Bajarildi | 120 s chunk, har chunk segment + JSON, sozlamalar kaliti (`cfg_key`) |
| FR-11 | JSON hisobot | Bajarildi | `<chiqish>.report.json`, har kadr uchun ma'lumot (9.3-bo'lim) |
| FR-12 | `--preview N`, yonma-yon | Bajarildi | CLI `--preview SEC`, UI tugmasi (30 s) |
| FR-13 | Grafik interfeys (yangi) | Bajarildi | tkinter, navbat, progress, to'xtatish va davom ettirish (9.1-bo'lim) |
| FR-14 | Portativ paket (yangi) | Bajarildi | `runtime\` ichida Python, ffmpeg, Maxine SDK (11-bo'lim) |
| FR-15 | Ishga tushishda muhit tekshiruvi (yangi) | Bajarildi | `gui.doctor()`: GPU, drayver ≥ 570, SDK va GPU arxitekturasi mosligi |
| FR-16 | Tuzatish kuchi sozlamasi (yangi) | Bajarildi | `--lid-open 0..1`, UI slayderi, default 0.5 |

## 5. Nofunksional talablar

| ID | Talab | Maqsad | O'lchangan (RTX 5070 Ti) | Holat |
|----|-------|--------|--------------------------|-------|
| NFR-1 | Tezlik, 1080p30, 25 min | ≤ 10 min | 62-70 kadr/s. 1080p25: 9-10 min. 1080p30: ~11-12 min (hisob). `--no-upscale` bilan ~83 kadr/s, 1080p30 ~9 min | 1080p25 bajarildi; 1080p30 default bilan chegaradan oshadi |
| NFR-2 | Tezlik, 4K30, 25 min | ≤ 30 min | O'lchanmagan | Ochiq |
| NFR-3 | VRAM | ≤ 12 GB | 0.9 GB (1080p) | Bajarildi |
| NFR-4 | RAM | ≤ 48 GB | 1.7 GB pik (python + ffmpeg jarayonlari) | Bajarildi |
| NFR-5 | Vaqtinchalik disk | ≤ 2 × kirish | Pik = segmentlar + yakuniy fayl ≈ 5.8 GB ≈ 2.4 × kirish (test: 2.4 GB kirish, 3.0 GB chiqish) | Biroz oshadi: chiqish bitrate kirishdan 1.5 barobar |
| NFR-6 | Deterministik chiqish | bit-identik | Foydalanuvchi qarori bilan yumshatildi: qarorlar bir xil, piksellar GPU inference tufayli ±1 farq qilishi mumkin. Bit-aniqlik alohida tekshirilmagan | Yumshatilgan |
| NFR-7 | Uzilishda ma'lumot yo'qolmaydi | chunk checkpoint | Har chunk segment + JSON (vaqtinchalik fayl + `os.replace`). Oxirgi chunk natijasini o'chirib qayta ishga tushirish sinovi: 250/250 kadr | Bajarildi |

VRAM va RAM 2026-09-22 da 10 s 1080p klipda o'lchandi (nvidia-smi umumiy xotira farqi, jarayonlar working set yig'indisi).
Tezlik 13 minutlik videoning to'liq ishlanishidan olingan: 284-324 s.

## 6. Yuz shakli va sifatni saqlash

**IP-1. Mask chegarasi.** Maska Maxine'ning 68-nuqtali landmarklaridagi ko'z konturidan (36-41, 42-47) quriladi:
- kontur + 1 px (ko'z kengligining 4%);
- `lid_open > 0` bo'lsa maska **faqat yuqoriga** kengayadi: `0.42 × lid_open × ko'z kengligi` (24 px ko'zda
  `lid_open 0.5` → 5 px). Pastki qovoq va ko'z burchaklari original qoladi;
- chegara Gauss bilan yumshatiladi, σ = ko'z kengligining 7.5% (~1.8 px).

v1.0 dagi "15% dilatatsiya, 3-6 px feather" o'rniga torroq maska tanlandi: test videoda bitta ko'z atigi 24 px.
`--blend box` rejimida Maxine'ning xom natijasi ishlatiladi (ko'z 15% ochiqroq).

**IP-2. Mask tashqarisi bayt-aniq.** Qurilish bilan kafolatlanadi. Chiqish kadri kirishning dekodlangan yuv420p
baytlaridan olinadi. Faqat haqiqatan o'zgargan piksellar yoziladi: Y har piksel bo'yicha, U/V kamida bitta o'zgargan
pikselli 2×2 blok bo'yicha. O'lchov (10 s, lossless):
- kadrda median 1 123 Y piksel o'zgaradi (kadrning 0.05%), hammasi ko'z atrofidagi ~110×37 px to'rtburchak ichida;
- to'rtburchak tashqarisida farq 0 (`mask_leak == 0`, 3 chunk, seek bilan);
- to'rtburchak ichidagi o'zgarmagan piksellarda farq 0 (2026-09-22 dagi tuzatishdan keyin; oldin BGR→YUV qayta
  konvertatsiya ularni ham siljitardi: Y max 10, U/V max 22 daraja).

Chiqish keyin H.264 ga kodlanadi, kodlash yo'qotishi butun kadrga tegadi (10.3-bo'lim).

**IP-3. Butun yuzga generativ model ishlatilmaydi.** Maxine faqat ko'z hududini o'zgartiradi. Face swap, butun yuz
GAN yoki diffusion yo'q.

**IP-4. Identity.** ArcFace cosine o'xshashligi, to'liq videoda median 0.993, minimum 0.952 (chegara 0.97 / 0.93).

**IP-5. Ko'z geometriyasi.** v1.0 chegarasi ±10% edi. Foydalanuvchi tuzatish kuchini ko'rib `lid_open 0.5` ni
tanladi va 10-15% ochilishni qabul qildi, chegara 15% ga o'zgartirildi. To'liq videoda median farq 10.9%. Faqat yuqori
qovoq ko'tariladi, bu odam kameraga qaraganda ham tabiiy ro'y beradi. Pastki qovoq va ko'z burchaklari joyida qoladi.

**IP-6. Blink saqlanadi.** Blink soni nisbati 1.01 (chegara 0.95-1.05). Blink chegarasi moslashuvchan:
`EAR < 0.6 × video bo'yicha median EAR`. v1.0 dagi qat'iy 0.20 pastga qarab o'qiyotgan so'zlovchida deyarli hamma
kadrni blink deb olardi.

**IP-7. Aralashmaslik siyosati.** Amalda qanday bajarilgani:

| v1.0 sharti | Bajarilishi |
|---|---|
| Blink | Maxine `DetectClosure`. Iris toni kontur yopiq bo'lsa (< 20 px) qo'llanmaydi |
| Nigoh allaqachon kameraga | Tashqi qoida yo'q (FR-7) |
| Bosh yaw > 30°, pitch > 20° | Maxine ichki gisterezisi (Low/High) |
| Yuz juda kichik | Yuz 2-4× kattalashtirib beriladi. Maxine topa olmasa ishonchlilik < 0.15, kadr original |
| Landmark ishonchliligi < 0.7 | 0.15 ishlatiladi (Maxine namunasidagi qiymat). Test videoda median ishonchlilik 0.70, 0.7 chegarasi yarim kadrni o'tkazib yuborardi |
| Ko'z ustida okklyuziya | Maxine `DetectClosure` (okklyuziyani ham qamraydi) |

**IP-8. Vaqt bo'yicha barqarorlik.** Maxine `Temporal` filtri yoqilgan. Har chunk boshida 25 kadr "isitish" ishlanadi,
lekin yozilmaydi. Iris toni parametrlari EMA (α = 0.15) bilan silliqlanadi. Crop oynasi gisterezis bilan kam
qimirlaydi. Flicker nisbati 1.01 (chegara 1.5).

## 7. Arxitektura

### 7.1 Engine tanlovi

Variant A (Maxine) M2 qaror nuqtasida qabul qilindi, Variant B (o'z modeli) qurilmadi. Maxine C++ namunasi build
qilinmaydi: `nvARPose.dll` va `NVCVImage.dll` to'g'ridan Python `ctypes` bilan chaqiriladi, Visual Studio va CMake
kerak emas. Kirish va chiqish GPU'da BGR buferlar, CUDA stream va CUDA graph ishlatiladi.

Maxine'ning tuzatish kuchi chegarasi taxminan 68%. SDK'da kuch yoki nishon parametri yo'q (DLL satrlari tekshirildi),
ketma-ket 2-3 marta o'tkazish foyda bermaydi (og'ish 6.4° → 6.0° → 5.9°, iris xiralashadi).

### 7.2 Modullar

| Modul | Vazifa |
|---|---|
| `eyecontact/gui.py` | UI (tkinter): navbat, sozlamalar, progress, to'xtatish; ishga tushishda `doctor()` tekshiruvi |
| `eyecontact/theme.py` | Dizayn tokenlari (`design-system/tokens.json`, dark tema): ranglar, shriftlar, bo'shliq, radius, ttk uslublari |
| `eyecontact/widgets.py` | Dizayn tizimi komponentlari: Button, StatusBadge, ProgressBar, QueueRow/QueueList, Slider, Checkbox, PathField (Toolbar), LogPanel, DoctorBanner |
| `eyecontact/cli.py` | Buyruq qatori, sozlamalarni yig'ish, preview |
| `eyecontact/pipeline.py` | Chunk, threadlar, `FaceROI`, `redirect_frame`, `lid_mask`, `IrisTone`, YUV kompozit, resume, hisobot |
| `eyecontact/maxine.py` | `GazeRedirector`: Maxine SDK ctypes wrapper, SDK papkasini topish |
| `eyecontact/video_io.py` | ffmpeg: probe, kadr o'qish va yozish (rawvideo pipe), concat, split-screen, NVENC tekshiruvi, konteyner tanlash |
| `tools/eval.py` | Sifat metrikalari (dasturchi vositasi) |
| `tests/` | Smoke test, UI testi, 10 s test klip |

### 7.3 Ma'lumot oqimi

```
Kirish video
 ├─ ffmpeg dekod → bgr24 ──► yuz crop ×S ─► Maxine ─► o'zgarish (delta) ×1/S ─► qovoq maskasi ─► iris toni ─┐
 └─ ffmpeg dekod → yuv420p (xom baytlar) ─────────────────────────────────────────────────────────────────┤
                                            faqat o'zgargan piksellar BGR→YUV qilib yoziladi ◄─────────────┘
                                                              │
                                              NVENC (H.264/HEVC) ─► seg_k.mp4 + seg_k.json  (har 120 s)
Segmentlar ─► ffmpeg concat (-c copy) + audio kirishdan (-c copy) ─► chiqish fayl + report.json
```

Uchta thread: o'quvchi (ikkala dekoder), asosiy (Maxine va kompozit), yozuvchi (enkoder). Navbatlar 8 kadrdan.

### 7.4 Asosiy algoritmlar

**Yuzni kattalashtirish (`FaceROI`).** Kichik yuzda Maxine irisni kulrang va xira chizadi. Shuning uchun Maxine'ga
ko'zlar atrofidagi crop butun son S marta kattalashtirib beriladi:
- S ∈ {1, 2, 3, 4}, kadr o'lchamini 2S ga bo'lishi shart; yuz kattalashtirilgandan keyin kadr balandligining ~60% bo'ladi.
  Test videoda S = 3: 640×360 crop 1920×1080 ga kattalashtiriladi;
- crop **ko'zlar o'rtasiga** markazlanadi. Maxine nigohni rasm markaziga nisbatan o'lchaydi: ko'z markazdan 300 px
  chetda bo'lsa o'qish ~15° ga siljiydi va ichki 20/30° chegaralari noto'g'ri ishlaydi;
- gisterezis: S ideal nisbat S ± 0.75 dan chiqqanda, joy ko'zlar crop o'lchamining 8% dan ko'p siljiganda o'zgaradi.
  Koordinatalar juft, har chunk boshida qayta aniqlanadi;
- yuz yo'qolsa (ishonchlilik < 0.15) keyingi kadrda alohida detektor (Maxine, redirect o'chiq) bilan qayta topiladi.

**O'zgarishni qaytarish.** Maxine natijasi va kattalashtirilgan kiruvchi rasm ayirmasi (delta) 2S ga tekislangan
to'rtburchakda olinadi, `INTER_AREA` bilan S marta kichraytiriladi va original piksellarga qo'shiladi. Maxine tegmagan
piksellarda delta 0, ular original qoladi.

**Qovoq maskasi (`lid_mask`).** IP-1 da tavsiflangan. Aralashtirish: `natija = original + (maxine − original) × maska`.

**Iris toni (`IrisTone`).** Maxine irisni originaldan och chizadi: ko'z ichidagi 8-persentil yorqinlik 53 → 78
(0-255 shkala). Tuzatish:
- maska ichida original va natijaning 8-persentili hamda natijaning 85-persentili olinadi, EMA (α = 0.15) bilan silliqlanadi;
- natija yorqinligi 85-persentildan pastda chiziqli ravishda original darajaga tushiriladi, faqat qoraytiriladi
  (koeffitsiyent 0.45-1.0), rang nisbati saqlanadi;
- natija originaldan qorong'i bo'lsa yoki kontur yopiq bo'lsa (blink) qo'llanmaydi.

Natija: yorqinlik 62, iris to'qroq va aniqroq.

**YUV kompozit.** Ikki dekoder bir xil kadrlarni beradi: Maxine uchun bgr24, chiqish uchun yuv420p xom baytlar.
BGR→YUV konvertatsiya dekoderdagi matritsa va diapazon bilan bir xil (test videoda BT.709, to'liq diapazon).
Faqat o'zgargan piksellar yoziladi (IP-2).

**Chunk va resume.** Chunk 120 s (25 kadr/s da 3000 kadr). Kadrga aniq seek:
`-ss = stream start_time + (start − 0.5) / fps` va `-frames:v`. Har chunk alohida segment bo'lib kodlanadi va JSON
checkpoint yoziladi. `--resume` segmentni faqat JSON dagi sozlamalar kaliti joriy sozlamalarga teng bo'lsa qayta
ishlatadi. Kalitga kirish fayli identifikatori ham kiradi (hajm, `mtime_ns`, boshidagi va oxiridagi 1 MB ning
xxhash64'i, EC-3): bir xil nomli boshqa video bilan eski chunklar ishlatilmaydi. Oxirida segmentlar `-c copy` bilan
birlashtiriladi, audio kirishdan nusxalanadi, vaqtinchalik papka o'chiriladi. Concat'da video
`video start_time − fayl start_time` ga suriladi (`-itsoffset`), chunki ffmpeg audioni fayl boshiga nisbatan siljitadi,
segmentlar esa 0 dan boshlanadi: (video − audio) farqi kirishdagidek qoladi (EC-1).

**VFR (EC-2).** Kadr soni `round(video davomiyligi × fps)`. VFR'da kadrlar `-copyts` + `fps` filtri + `trim=start_pts`
bilan o'qiladi: kadr to'ri butun fayl uchun absolyut vaqtda bir xil, chunk chegarasida siljish yo'q. Seek 1 s
oldinroqdan, tushgan kadr o'rnini oldingisi to'ldiradi. Natija butun faylni `fps` filtri bilan o'qilgan ideal CFR
ketma-ketlik bilan kadrma-kadr teng.

### 7.6 Patch rejimi (`--patches-out`, EC-4, Dars Studio uchun)

Video kodlanmaydi. Har chunk uchun `DIR/chunk_XXXXX.npz` (zlib) va `chunk_XXXXX.json` (checkpoint, resume), oxirida
`DIR/meta.json`: format versiyasi, `source_id` (kirish fayli identifikatori), o'lcham, fps, `pix_fmt` (yuv420p),
rang matritsasi va diapazon, `cfg_key`, chunklar ro'yxati. npz ichida har patchli kadr uchun: `frame_idx`, `box`
(x0, y0, x1, y1), bitpack `y_mask`/`uv_mask` (faqat baytlari o'zgargan piksellar), `y_data`, `uv_data` (U keyin V),
`offsets`, `size`. `eyecontact/patches.py`: `write_chunk`, `read_chunk`, `apply(frame_yuv, rec, w)`:
`out = orig + w·(patch − orig)` maska ichida; `w = 1` da oddiy rejim chiqishi bilan bayt-aniq (Y va UV, stub testida
360 kadrda tekshirilgan). Hajm: 10 s 1080p25 klipda 384 KB (25 min ≈ 56 MB).

### 7.5 Maxine sozlamalari

| Parametr | Qiymat |
|---|---|
| Landmarks_Size | 68 |
| Temporal | yoqilgan (0xFFFFFFFF) |
| GazeRedirect | 1 (detektor nusxasida 0) |
| EnableLookAway | 0 |
| UseCudaGraph | 1 |
| EyeSizeSensitivity | 2 (`--eye-size`) |
| Gaze Pitch/Yaw Threshold Low / High | 20° / 30° (`--max-gaze`) |
| Head Pitch Threshold Low / High | 15° / 20° (`--max-head-pitch`) |
| Head Yaw Threshold Low / High | 25° / 30° (`--max-head-yaw`) |
| Yuz yo'q chegarasi | o'rtacha landmark ishonchliligi < 0.15 |

Gaze vektor tartibi empirik aniqlandi: `[0]` = pitch, `[1]` = yaw (kadr gorizontal aylantirilganda `[0]` o'zgarmaydi).
SDK hujjatida teskari yozilgan.

## 8. Kirish va chiqish

Kirish:
- Konteyner MP4, MOV, MKV; kodek H.264, H.265, ProRes (ffmpeg dekodlay oladigan har qanday). Sinovdan o'tgani: H.264 MOV.
- 8-bit 4:2:0. Boshqa piksel formati bo'lsa xato bilan to'xtaydi.
- O'zgaruvchan kadr tezligi (VFR) doimiyga o'tkaziladi, ogohlantirish chiqadi (7.4, sintetik VFR testida tekshirilgan).
- Rotation metadata hisobga olinadi.

Chiqish:
- Video H.264 NVENC (`-preset p7 -tune hq`, VBR), bitrate kirish × 1.5, maksimal bitrate undan 1.5 barobar yuqori,
  bufer 2 barobar. `--codec hevc` bilan HEVC. NVENC ishlamasa CPU libx264/libx265.
- Audio `-c:a copy`. Audio PCM bo'lsa konteyner `.mov`, chunki PCM MP4 ichida ko'p player va montaj dasturida ovozsiz.
- Rang teglari (diapazon, matritsa, primaries, transfer) kirishdan ko'chiriladi. `+faststart`.
- `--lossless`: FFV1, MKV (baholash uchun).
- Preview: original va natija yonma-yon, H.264 NVENC cq 20, audio AAC 192 kbit/s.

Fayl nomlari (UI): `<nom>_eyecontact.mp4` yoki `.mov`, preview `<nom>_preview.mp4`, hisobot `<chiqish>.report.json`,
vaqtinchalik papka `<chiqish>.work` (tugagach o'chiriladi).

## 9. Foydalanish

### 9.1 UI

`EyeContact.bat` ni ikki marta bosish (ish stoli yorlig'i: `Ish_stoliga_yorliq.bat`).

- Ishga tushishda GPU, drayver va SDK tekshiriladi. Muammo bo'lsa tugmalar o'chiq qoladi va sababi xabar oynasida chiqadi.
- Bir nechta videoni navbatga qo'shish, tanlanganini olib tashlash, ro'yxatni tozalash.
- Chiqish papkasi (bo'sh bo'lsa video yonida).
- "Tuzatish kuchi" slayderi (`lid_open`, default 0.5), HEVC belgisi.
- «Boshlash»: videolar navbat bilan, har biri alohida jarayonda `--resume` bilan ishlanadi.
- «Preview (30 s, yonma-yon)»: tayyor bo'lgach o'zi ochiladi.
- «To'xtatish»: jarayon daraxti to'xtatiladi. Qayta «Boshlash» uzilgan chunkdan davom etadi.
- Progress: kadr, kadr/s, qolgan vaqt; pastda jurnal; har video holati: navbatda, ishlanmoqda N%, tayyor, to'xtatildi, xato.
- «Natija papkasini ochish». Sozlamalar `gui_settings.json` da saqlanadi. Yuqori DPI ekranlarga moslashgan.
- Ko'rinish `design-system/` bo'yicha (2026-09-22): dark tema, har bir navbat qatorida StatusBadge va faqat
  ishlanmoqda/to'xtatildi holatida ProgressBar, `doctor()` muammosi oyna tepasidagi DoctorBanner'da.

### 9.2 Buyruq qatori

```
runtime\python\python.exe -m eyecontact.cli IN OUT [opsiyalar]
```

| Opsiya | Default | Ma'no |
|--------|---------|-------|
| `--lid-open 0..1` | 0.5 | Yuqori qovoq ochilishi, ya'ni tuzatish kuchi (10.4-bo'lim) |
| `--blend lid\|box` | lid | box: Maxine xom natija |
| `--no-iris-tone` | yoqilgan | Iris tonini tiklashni o'chirish |
| `--no-upscale` | yoqilgan | Yuzni kattalashtirishni o'chirish: tezroq (~83 kadr/s), iris xiraroq |
| `--eye-size 2..6` | 2 | Maxine EyeSizeSensitivity |
| `--no-temporal` | yoqilgan | Maxine temporal filtrini o'chirish |
| `--max-gaze`, `--max-head-yaw`, `--max-head-pitch` | 30, 30, 20 | Maxine High chegaralari, gradus (Low: 20, 25, 15) |
| `--codec h264\|hevc` | h264 | Video kodek |
| `--bitrate BPS` | kirish × 1.5 | 0 bo'lsa `--cq` ishlatiladi |
| `--cq` | 18 | NVENC cq yoki x264 crf |
| `--lossless` | — | FFV1/MKV |
| `--chunk-sec` | 120 | Chunk uzunligi |
| `--resume` | — | Tayyor chunklarni qayta ishlamaydi |
| `--patches-out DIR` | — | Video o'rniga ko'z patchlari (7.6); `OUT` kerak emas |
| `--preview SEC` | — | Birinchi SEC soniya, yonma-yon |
| `--workdir`, `--keep-work` | `OUT.work` | Vaqtinchalik segmentlar |
| `--report PATH` | `OUT.report.json` | Hisobot yo'li |
| `--progress` | — | UI uchun `PROGRESS` va `OUTPUT` satrlari |
| `-q` | — | Jim rejim |

Chiqish kodi: 0 muvaffaqiyat, 1 xato. `tools/eval.py`: 0 PASS, 2 FAIL.
Muhit o'zgaruvchisi `NVAR_SDK_DIR` Maxine SDK papkasini majburan belgilaydi.

### 9.3 Hisobot (`report.json`)

`input`, `output`, `frames_total`, `frames_changed`, `frames_skipped`, `skip_reasons` (yuz yo'q / Maxine o'zgartirmagan),
nigoh medianlari, `seconds`, `fps`, `config`, `input_meta` va `per_frame`: har kadr uchun gaze yaw/pitch, head yaw/pitch,
ishonchlilik, o'zgarganmi, o'zgarish to'rtburchagi.

## 10. Baholash (`tools/eval.py`)

Kirish: original, natija, `report.json`. Chiqish: `metrics.json` va PASS/FAIL. Dasturchi vositasi: `onnxruntime`,
`mediapipe` va `models/` papkasidagi modellar kerak (11.5-bo'lim), yo'q bo'lsa tegishli metrika SKIP.

### 10.1 Metrikalar

| Metrika | Usul | Chegara |
|---------|------|---------|
| identity median / min | ArcFace w600k_r50 (ONNX, CPU); ikkala kadr original landmarklar bilan tekislanadi | ≥ 0.97 / ≥ 0.93 |
| ear_drift | MediaPipe FaceLandmarker, yuz crop 2× (to'liq kadrda kichik yuzni topmaydi); median \|ΔEAR\| / EAR | ≤ 0.15 (v1.0 da 0.10, 13.2-bo'lim) |
| blink_count_ratio | Maxine 68-nuqta EAR har kadrda; blink = EAR < 0.6 × median, ≥ 2 kadr | 0.95-1.05 |
| flicker_ratio | Ko'z to'rtburchagida ketma-ket kadrlar farqi, natija / kirish | ≤ 1.5 |
| frame_count, duration | ffprobe | teng, ≤ 1 kadr |
| audio_hash | Audio stream md5 | teng |
| mask_leak | yuv420p, o'zgarish to'rtburchagi tashqarisi, faqat lossless natijada | 0 |
| gaze_success | Gaze360 ResNet-34, \|yaw\| va \|pitch\| ≤ 5° ulushi | ≥ 0.90, faqat ma'lumot uchun (10.5) |

### 10.2 Natijalar (to'liq video, 19 985 kadr)

| Versiya | O'zgarish | Identity median / min | EAR farqi | Blink | Flicker | Tezlik, kadr/s | Natija |
|---|---|---|---|---|---|---|---|
| v1 | Maxine xom natija | — | +17% (60 kadr) | — | — | 47.5 | Rad etildi (ko'z kattalashadi) |
| v2 | Qovoq konturi maskasi | 0.988 / 0.931 | 6.1% | 1.03 | 0.97 | 82.6 | PASS |
| v3 | + yuzni 3× kattalashtirish | 0.993 / 0.961 | 6.1% | 1.02 | 0.98 | 66-70 | PASS |
| v4 | + crop ko'zlar markazida, `lid_open` | to'liq baholanmagan | — | — | — | 63-70 | Foydalanuvchi 0.5 ni tanladi |
| **v5** | + faqat yuqoriga maska, iris toni (yakuniy default) | **0.993 / 0.952** | **10.9%** | **1.01** | **1.01** | 62-70 | **PASS** |

v2, v3 va v5 da kadr soni, davomiylik va audio md5 originalga teng. Identity va MediaPipe har 25-kadrda o'lchangan.

10 s klip, lossless, yakuniy sozlamalar: identity 0.995 / 0.968, EAR farqi 12.0%, blink 1.00, flicker 1.02,
`mask_leak` 0.

2026-09-22 da IP-2 tuzatishi kiritildi (faqat o'zgargan piksellarni yozish). To'liq baholash undan keyin qayta
o'tkazilmagan: baholash modellari paketdan olib tashlangan. Tuzatish faqat maska tashqarisidagi yaxlitlash farqini
yo'qotadi, smoke test (kadr soni, audio, `mask_leak`, o'zgarmagan piksellar) o'tdi.

### 10.3 Kodlash sifati

v2 fayli, 60-120 s oralig'i (1 500 kadr), original bilan solishtirilgan. Kodlash sozlamalari v5 da o'zgarmagan.

| Metrika | Natija | Ko'zga ko'rinmaslik chegarasi |
|---|---|---|
| VMAF | 97.8 | > 95 |
| PSNR o'rtacha / eng past kadr | 55.0 / 51.8 dB | > 45 dB |
| SSIM | 0.9986 | > 0.99 |

### 10.4 Nigoh tuzatish kuchi

Uch joydan 120-150 kadr. Nigoh Maxine estimatori bilan, ko'zlar markazda turgan 3× crop ustida o'lchangan.

| Variant | Qolgan og'ish | Tuzatish | Ko'z ochiqligi |
|---|---|---|---|
| Original | 7.7° | — | — |
| `lid_open 0` (qovoq qat'iy saqlanadi) | 5.0° | 35% | +7% |
| `lid_open 0.5`, har tomonga kengaygan maska | 3.1° | 59% | +12% |
| **`lid_open 0.5`, faqat yuqoriga + iris toni (default)** | **2.8°** | **63%** | **+13%** |
| `lid_open 1` | 2.7° | 66% | +14% |
| `--blend box` (Maxine xom) | 2.5° | 68% | +15% |
| Uchinchi tomon vositasi | 1.3° | 84% | +19% |

Xulosa: pastga tushgan qovoqning o'zi "pastga qarayapti" belgisi. Qovoqni qanchalik saqlasak, tuzatish shunchalik
sustlashadi. 68% dan yuqorisi uchun boshqa engine kerak.

### 10.5 Avtomatik nigoh metrikasi haqida

Mustaqil estimatorlar (Gaze360, MediaPipe iris) bu videoda bir-biriga mos kelmaydi va kadrni oynada aylantirish
testida ±7° sochiladi: yuz kichik, ko'z 24 px. Shuning uchun `gaze_success` PASS/FAIL ga kirmaydi. 10.4 dagi raqamlar
Maxine'ning o'z estimatori bilan olingan, ya'ni mustaqil emas. Tuzatish yo'nalishi 8× zoomdagi vizual taqqoslash va
uchinchi tomon natijasi bilan solishtirish orqali tasdiqlandi. Ishonchli avtomatik o'lchov uchun yuz kadr balandligining
kamida 35% bo'lgan klip kerak.

### 10.6 Sub'ektiv baholash

v1.0 dagi 5 kishilik test (10 juftlik) o'tkazilmagan. Foydalanuvchi yonma-yon klipni (original, `lid_open 0`,
`lid_open 0.5`) ko'rib 0.5 ni tanladi.

## 11. Muhit va paket

### 11.1 Sinov apparati

Intel i7-14700K, 64 GB RAM, NVIDIA GeForce RTX 5070 Ti 16 GB (Blackwell), Windows 11 Pro, NVIDIA drayver 591.86.

### 11.2 Paket tarkibi (jami ~1.9 GB)

| Papka | Hajm | Tarkib |
|---|---|---|
| `runtime/python` | 245 MB | Python 3.11.16 (python-build-standalone, ko'chiriladigan), tkinter, numpy 2.4.6, opencv-python-headless 5.0.0.93 |
| `runtime/ffmpeg` | 282 MB | ffmpeg va ffprobe 7.1.1 (gyan.dev full build) |
| `runtime/maxine` | 1.37 GB | Maxine AR SDK v0.8.7, Blackwell: `nvARPose.dll`, `NVCVImage.dll`, TensorRT 10, CUDA 12 runtime, cuBLAS, cuFFT 11, NPP, VPI; 7 ta model; `ARCH.txt` |
| `eyecontact`, `tools`, `tests` | 18 MB | Dastur kodi, baholash vositasi, testlar va 10 s klip |

Maxine SDK Program Files'ga o'rnatilmasdan `add_dll_directory` bilan paket ichidan ishlaydi, registry va PATH kerak emas.
SDK nusxasi qisqartirilgan: faqat kerakli modellar qoldirilgan (`face_detection`, 4 ta `faceland`, `gazeredir` encoder va
decoder), `cufft64_10` va `cufftw` kutubxonalari kerak emas (`cufft64_11` kerak).

SDK papkasini tanlash tartibi: `NVAR_SDK_DIR` → `runtime/maxine` (GPU arxitekturasi `ARCH.txt` ga mos bo'lsa) →
`C:\Program Files\NVIDIA Corporation\NVIDIA AR SDK`. UI `doctor()` bilan mos variantni topib, CLI jarayoniga uzatadi.

### 11.3 Qo'llab-quvvatlanadigan GPU

| GPU | Maxine SDK | Holat |
|---|---|---|
| RTX 50 (Blackwell) | Paket ichida | Sinalgan (RTX 5070 Ti) |
| RTX 40 (Ada) | `SDK_ornatish.bat` bir marta ishga tushiriladi | Sinalmagan |
| RTX 30 (Ampere) | `SDK_ornatish.bat` | Sinalmagan |
| RTX 20 (Turing) | `SDK_ornatish.bat` | Sinalmagan |
| NVIDIA RTX yo'q | — | Ishlamaydi, UI sababini aytadi |

`SDK_ornatish.bat` GPU ni aniqlab, mos installerni yuklaydi (~1.3 GB) va jim rejimda o'rnatadi. Internet va
administrator ruxsati kerak. Minimal drayver 570.

### 11.4 Litsenziyalar

Paket tarqatilsa: NVIDIA Maxine EULA va uchinchi tomon litsenziyalari (`runtime/maxine`), ffmpeg GPL
(`runtime/ffmpeg/LICENSE.txt`), Python PSF litsenziyasi (`runtime/python`).

### 11.5 Tashqi manbalar

| Nima | Manba |
|---|---|
| Maxine AR SDK installer | `https://international.download.nvidia.com/Windows/broadcast/sdk/AR/nvidia_ar_sdk_installer_v0.8.7_<blackwell\|ada\|ampere\|turing>.exe` |
| ArcFace (eval) | `https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip` → `w600k_r50.onnx` |
| MediaPipe (eval) | `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task` |
| Gaze360 (eval) | `https://github.com/yakhyo/gaze-estimation/releases/download/weights/resnet34_gaze.onnx` |

Baholash uchun: `runtime\python\python.exe -m pip install -r requirements-eval.txt`, modellar `models/` papkasiga.

## 12. Loyiha tuzilishi

```
eye contact/
  EyeContact.bat              dasturni ochish
  Ish_stoliga_yorliq.bat      ish stoliga yorliq
  SDK_ornatish.bat / .ps1     RTX 40/30/20 uchun mos Maxine SDK ni o'rnatish
  README.md                   foydalanish qo'llanmasi
  TEXNIK_TOPSHIRIQ.md         shu hujjat (v2.0)
  TEXNIK_TOPSHIRIQ_v1.0.md    dastlabki talablar
  requirements.txt            numpy, opencv (runtime ichida o'rnatilgan)
  requirements-eval.txt       onnxruntime, mediapipe (faqat baholash uchun)
  eyecontact/                 gui.py, theme.py, widgets.py, cli.py, pipeline.py, maxine.py, video_io.py
  design-system/              UI dizayn tizimi (README.md, tokens.json, components/)
  assets/eyecontact.ico       logotip (Cover motividan, tools/make_icon.py)
  tools/eval.py               baholash
  tests/                      test_smoke.py, test_gui.py, clip_10s.mp4
  runtime/                    python/, ffmpeg/, maxine/
```

Testlar:
```
runtime\python\python.exe tests\test_smoke.py   # 10 s klip, 3 chunk: kadr soni, audio md5, mask_leak, o'zgarmagan piksellar
runtime\python\python.exe tests\test_gui.py     # UI odamsiz: video qo'shish, ishlash, natijani tekshirish
```

v1.0 dagi `face.py`, `smooth.py`, `gaze.py`, `blend.py`, `make_preview.py` qurilmadi: ularning vazifasi Maxine ichida yoki
`pipeline.py` va `--preview` da bajariladi.

## 13. Bajarilgan ishlar

### 13.1 Bosqichlar

| Sana | Bosqich | Natija |
|---|---|---|
| 2026-09-18 | v1.0 tahlili, muhit tekshiruvi, savollar | Qarorlar (13.2), test video tanlandi |
| 2026-09-18 | M0: Maxine SDK o'rnatish, ctypes wrapper, preview | Ishladi: Maxine 133, dekod 96, NVENC 156 kadr/s |
| 2026-09-18 | M1: pipeline (chunk, YUV kompozit, resume), smoke test, `eval.py` | `mask_leak` 0, audio teng |
| 2026-09-18 | M2: Variant A qabul qilindi | Variant B qurilmaydi |
| 2026-09-18 | v1: to'liq video, Maxine xom natija | Ko'z 17-27% kattalashadi, rad etildi |
| 2026-09-18 | v2: qovoq konturi maskasi, tezlik optimizatsiyasi | EAR 6%, 82.6 kadr/s, PASS |
| 2026-09-18 | Audio muammosi | PCM uchun `.mov` konteyner |
| 2026-09-18 | v3: yuzni kattalashtirish | Iris aniq, identity 0.993 |
| 2026-09-18 | v4: nigoh o'lchovi tuzatildi, crop ko'zlar markazida, `lid_open` | Tuzatish 35-68% oralig'ida sozlanadi |
| 2026-09-18 | v5: faqat yuqoriga maska, iris toni, default 0.5 | 63% tuzatish, PASS |
| 2026-09-18 | UI (tkinter), o'rnatuvchi | Odamsiz UI testi o'tdi |
| 2026-09-22 | Tozalash, portativ paket, `doctor()`, `SDK_ornatish.bat` | 1.9 GB, o'rnatishsiz ishlaydi |
| 2026-09-22 | IP-2 tuzatishi, VRAM/RAM o'lchovi, shu hujjat | O'zgarmagan piksellar bayt-aniq |
| 2026-10-26 | Dars Studio uchun EC-1..EC-5 (`studio-ec` branch) | GPU'siz stub testlari (11), A/V siljish, VFR, resume kaliti, `--patches-out` |

### 13.2 Qabul qilingan qarorlar

| Qaror | Kim | Sabab |
|---|---|---|
| Test video `DSBA8944.MOV` | Foydalanuvchi | Haqiqiy ish videosi, ko'zoynakli so'zlovchi |
| Chiqish montaj dasturi (Premiere/DaVinci) uchun, H.264, bitrate kirish × 1.5 | Foydalanuvchi | Vizual yo'qotish bo'lmasin; DaVinci bepul versiyasi Windows'da HEVC ochmaydi |
| Determinizm: qarorlar bir xil, piksel ±1 | Foydalanuvchi | GPU inference bit-aniq emas |
| UI, README va jurnallar o'zbek tilida | Foydalanuvchi | — |
| Variant A (Maxine) | M2 natijasi | Barcha metrikalar o'tdi |
| Default `lid_open 0.5`, EAR chegarasi 15% | Foydalanuvchi | Yonma-yon klipni ko'rib tanladi: tuzatish deyarli 2 barobar kuchli |
| UI qo'shish | Foydalanuvchi | Buyruq qatorisiz ishlatish |
| Portativ paket, eski natijalarni o'chirish | Foydalanuvchi | Istalgan kompyuterda nusxalab ishlatish |

## 14. Xavflar va topilgan muammolar

| # | Muammo | Sabab | Yechim |
|---|---|---|---|
| 1 | NVENC ishlamadi: "Required: 13.1 Found: 13.0" | ffmpeg 9 drayver ≥ 610 talab qiladi | ffmpeg 7.1.1; NVENC bo'lmasa CPU x264 |
| 2 | Lossless natijada butun kadr o'zgargan | ffmpeg 7 rawvideo kirishida rang teglari bo'lmasa diapazon konvertatsiyasi qo'shadi | Kirish va chiqishga bir xil rang teglari |
| 3 | Video 0.053 s ga siljigan, kadr soni noto'g'ri | Test klipda audio salbiy pts; seek stream `start_time` ni hisobga olmagan | Seek `start_time` bilan; MKV da kadrlar paket bo'yicha sanaladi |
| 4 | Box ichidagi o'zgarmagan piksellar siljigan (Y max 10, U/V max 22) | BGR→YUV qayta konvertatsiya | Faqat o'zgargan piksellar yoziladi (2026-09-22) |
| 5 | Natija videoda ovoz yo'q | PCM MP4 ichida `ipcm` tegi bilan, ko'p dastur o'qimaydi | Audio PCM bo'lsa `.mov` (`sowt` tegi) |
| 6 | Ko'z 17-27% kattalashgan | Maxine xom natijasi qovoqni ko'taradi | Qovoq konturi maskasi, keyin faqat yuqoriga kengayadigan maska |
| 7 | Iris kulrang va xira | Yuz kichik (230 px) | Yuzni 2-4× kattalashtirib berish, iris toni |
| 8 | Nigoh "20° pastga" o'qilgan, tuzatish qisman o'chgan | Maxine burchakni rasm markaziga nisbatan o'lchaydi | Crop ko'zlar o'rtasiga markazlanadi |
| 9 | Gaze vektor tartibi noaniq | SDK hujjati teskari | Oyna testi: `[0]` = pitch, `[1]` = yaw |
| 10 | Tezlik 47 kadr/s | O'zgarish to'rtburchagini topish 16 ms/kadr | 2D taqqoslash, 2.3 ms |
| 11 | MediaPipe yuzni topmagan | Kadrda yuz kichik | Yuz crop 2× |
| 12 | Avtomatik nigoh metrikalari bir-biriga zid | Ko'z 24 px, estimatorlar ±7° | `gaze_success` faqat ma'lumot uchun |
| 13 | Qat'iy blink chegarasi (0.20) ishlamaydi | Pastga qaragan so'zlovchida EAR doimo past | Moslashuvchan chegara 0.6 × median |
| 14 | Portativ Python'ga paket o'rnatilmadi | `EXTERNALLY-MANAGED` belgisi | Belgi olib tashlandi |
| 15 | `nvARPose.dll` yuklanmadi | Qisqartirilgan SDK da `cufft64_11.dll` yo'q edi | `cufft64_11.dll` qaytarildi |
| 16 | UI drayverni "592" deb ko'rsatgan | Yaxlitlash | Aniq qiymat (591.86) |
| 17 | Chiqishda video va audio boshlanishi farqi yo'qolgan: 52 ms siljishli MOV'da 0 ga, `clip_10s` da (ikkalasi 0.08 s) video 0.00 / audio 0.08, ya'ni ovoz 80 ms kech | Segmentlar 0 dan boshlanadi, audio fayl boshiga nisbatan copy qilinadi | Video `-itsoffset` = video start − fayl start (EC-1); `eval.py` da `av_offset_ms` |
| 18 | VFR klipda (6 kadr tushgan) chiqish 0.2 s qisqa, chunkdan keyin 1 kadr siljish | Kadr soni paketlardan; `-fps_mode cfr` to'rni seek nuqtasidan quradi | `round(davomiylik × fps)`; `-copyts` + `fps` filtri (EC-2) |
| 19 | Shu nomli boshqa video bilan `--resume` eski chunklarni qo'shib yuborishi mumkin | `cfg_key` faqat sozlamalardan | Kalitga fayl identifikatori (EC-3) |
| 20 | Maxine bir xil kirishda ikki marta ishga tushirilganda lossless chiqish farq qiladi: max 3, 250 kadrda ~870 bayt | GPU inference (temporal filtr) bit-aniq emas | Qaror "piksel ±1" amalda ±3; regressiya shu shovqin bilan solishtiriladi |

Ochiq xavflar: 4K da sifat va tezlik, boshqa GPU avlodlari, ko'zoynaksiz va katta yuzli videolar (16-bo'lim).

## 15. Qabul mezonlari holati (v1.0, 15-bo'lim)

| # | Mezon | Holat |
|---|---|---|
| 1 | 10-bo'lim metrikalari 3 videoda PASS: 1080p30 25 min, 4K30 20 min, ko'zoynakli 1080p 5 min | Qisman: 1 video (1080p25, 13 min, ko'zoynakli) PASS. Boshqa videolar berilmagan |
| 2 | NFR-1, NFR-2 | NFR-1 1080p25 uchun bajarildi, 1080p30 default bilan ~11-12 min. NFR-2 o'lchanmagan |
| 3 | `--resume` uzilishda to'g'ri davom etadi, bit-identik | Qisman: chunkni o'chirib qayta ishga tushirish sinovi o'tdi (kadr soni, audio). Bit-aniqlik tekshirilmagan (NFR-6 yumshatilgan) |
| 4 | Sub'ektiv test | O'tkazilmagan. Foydalanuvchining vizual tanlovi bor |
| 5 | README | Bor |

## 16. Ochiq masalalar va keyingi qadamlar

1. **Sub'ektiv test.** 5 kishi, 10 juftlik, "yuz o'zgarganmi" va "ko'z tabiiymi" savollari.
2. **Qo'shimcha videolarda sinov.** 25 minutlik, 4K, 30 kadr/s, ko'zoynaksiz so'zlovchi, yuzi kattaroq kadr.
3. **Boshqa GPU'larda sinov.** RTX 40/30/20 da `SDK_ornatish.bat` yo'li.
4. **1080p30 tezligi.** Default bilan NFR-1 dan oshadi. Kerak bo'lsa: `--no-upscale` yoki pipeline optimizatsiyasi.
5. **To'liq baholashni qayta o'tkazish.** 2026-09-22 dagi IP-2 tuzatishidan keyin (baholash modellari va paketlarini
   qayta yuklash kerak).
6. **Kuchliroq tuzatish.** 68% dan yuqorisi Maxine bilan erishilmaydi, o'z modeli (Variant B) kerak: haftalik ish,
   yuz o'zgarishi xavfi bor.
7. **10-bit va HDR** qo'llanmaydi.
8. **Git.** Repozitoriy yaratilgan, lekin commit yo'q. `runtime/` hajmi katta bo'lgani uchun `.gitignore` da, paket
   papkani nusxalash orqali tarqatiladi.
9. **Test klip.** `tests/clip_10s.mp4` so'zlovchining haqiqiy videosidan kesilgan. Paket boshqalarga berilsa, uni olib
   tashlash yoki almashtirish mumkin: dastur ishiga ta'sir qilmaydi, faqat testlar uchun.
