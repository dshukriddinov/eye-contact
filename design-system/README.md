Eye Contact is a portable Windows tool that redirects a talking-head speaker's gaze toward the camera in an already-recorded video, frame by frame, on an NVIDIA RTX GPU. It runs unattended for 10–30 minutes on a single clip; the window's whole job while that happens is to say, without ambiguity, what state every queued file is in and why nothing outside the eyes has changed. Built from `TEXNIK_TOPSHIRIQ.md` v2.0 (2026-09-22): its component and status names, and every UI string quoted below, are the spec's own — no ready-made component set behind this, so the inventory here is deliberately small and grows only as the real window does.

## Voice

- Do: short, literal Uzbek sentences that name the object and the state — "Video qoʻshildi", "Ishlanmoqda 42%", "GPU topilmadi". Numbers always carry their unit: "67 kadr/s", "13 min 19 s", "0.9 GB".
- Do: state a failure's cause the way the spec's own error table does (14-boʻlim) — "drayver ≤ 570" reads as a fact to act on, not a rebuke.
- Don't: exclamation marks, marketing adjectives ("ajoyib", "kuchli"), or an English word where an Uzbek one already exists in the spec.
- Don't: invent new terms for things the spec already names — reuse Navbat, Jurnal, Tuzatish kuchi, Boshlash, Toʻxtatish, Preview exactly.

## Colour

Two themes, dark first: this wraps a GPU video pipeline meant to run beside Premiere, DaVinci and NVIDIA's own Maxine tooling, all dark by default, often in a dim edit bay. Light is a fully seeded second theme, not a tint of the dark one — every token has its own light value, and both meet the ratios below.

`surface-100/200/300/400` step from window background to panel to hovered row to a control's own track — nest them in that order, never skip a step (a row on `surface-100` reads as floating). `ink`, `ink-secondary` and `ink-tertiary` are a strict hierarchy: `ink` for anything read as content (filenames, buttons, dialog copy), `ink-secondary` for supporting text, `ink-tertiary` only for placeholder text and a disabled control's own label — never for a status word, which always takes its status colour so it survives a screenshot with `ink-tertiary` misread as "disabled."

`accent` is not decoration: it is the one colour that means "this file is being worked on right now" — the active queue row's status text, its progress fill, the slider's filled track and thumb, and the primary action (`Boshlash`). A queued row, an idle slider and a hovered menu item never borrow it. `success`, `danger` and `muted` are the other three queue states (`Tayyor`, `Xato`, and `Navbatda`/`Toʻxtatildi` share `muted` — see Status colour below); each has a `-subtle` tint for its pill's background and, where text sits on a solid fill instead, an `on-…` token — never plain white or black on a coloured fill.

**Status colour.** `Navbatda` (queued) and `Toʻxtatildi` (stopped) both read as "not currently happening" and share `muted`/`muted-subtle`; they're told apart by their word, never by colour alone. `Ishlanmoqda` (processing) is `accent`/`accent-subtle`. `Tayyor` (done) is `success`/`success-subtle`. `Xato` (error) is `danger`/`danger-subtle`. Every pill carries its Uzbek word — colour is reinforcement, never the only signal, so the system stays legible to a colour-blind editor without any extra theme.

**Contrast, checked in both themes:** every text colour holds at least 4.5:1 on every surface its token note names (`ink-tertiary` 4.57:1 dark / 4.56:1 light on `surface-300`, its tightest pair); a status colour on its own `-subtle` tint holds at least 4.5:1 (`accent` on `accent-subtle` is the tightest, 4.60:1 in light). Non-text marks that carry meaning — the focus ring, a status icon, `accent-strong` used as a border — hold at least 3:1 (`accent-strong` on `surface-200` is 5.67:1 dark, 8.01:1 light). `border` and plain `border-strong` are decorative only and are exempt: nothing depends on seeing them to know a control's state.

## Type

One native family, `Segoe UI` (`sans`), because this ships only for Windows 10/11 and the portable package installs nothing — no font files travel with it, unlike the video and GPU runtimes it does bundle (11-boʻlim). `mono` (Cascadia Mono, falling back to Consolas) is reserved for anything that updates in place — the frame/kadr⁄s/ETA row and the log console — so tabular figures don't jitter as they tick over; it never appears in a button or a filename.

Six sans steps, smallest first in daily use: `caption` for timestamps and fine print, `label` for a field's own caption ("Tuzatish kuchi"), `body` for everything a person reads or clicks, `body-strong` for the emphasised word inside body text (a status word, a dialog's default action), `heading` for a panel title (Navbat, Jurnal), `display` for the app name on the cover and the About panel only — it never appears inside the working window itself, which has no room for it.

## Spacing, radius, layout

A 4px grid (`space-1`–`space-6`) sized for a dense utility window: `space-2` inside a chip or button, `space-3` inside a queue row, `space-4` as panel padding and between toolbar groups, `space-5` between the queue and the log, `space-6` as the outer window margin. Radii stay small — `radius-sm` on chips and checkboxes, `radius-md` on buttons, fields and queue rows, `radius-lg` on panels and the preview frame, `radius-full` only on a status pill or the slider thumb; nothing in this window is a rounded card. Every size here is expressed in CSS px against that one grid, never a fixed dialog unit, so the layout holds up on the high-DPI displays the spec calls out (9.1-boʻlim) without a second set of measurements. Keep any clickable target at least 32px tall.

## Iconography

No icon set shipped with the spec, so none is invented here: use a single outline family on a 20px grid, 1.5px stroke, drawn with `currentColor` so an icon recolours by sitting inside `ink`, `accent`, `success`, `danger` or `muted` text — never a hard-coded fill. A small, fixed vocabulary covers the window: add-video, remove, folder, play (Boshlash), stop (Toʻxtatish), split-preview, and the four status glyphs (clock for navbatda, a spinner mark for ishlanmoqda, a check for tayyor, a triangle for xato). Flagged: source these from one licensed outline set (Lucide or an equivalent) and drop the files under `assets/Icons/` — nothing here approximates or fabricates a mark.

## Motion, elevation and states

Motion is instrumentation, not decoration: a progress fill's width transitions over 150–200ms ease-out, and nothing else animates — the frame count, fps and ETA figures snap to their new value every tick rather than tweening, because they are measured facts, not an estimate settling into place. Shadow is reserved for `overlay` — the preview window and any dialog floated above the main one — and appears nowhere else: a resting queue row or button sits flush on its panel, no card-and-shadow treatment, no coloured left border as a state marker.

Every interactive control defines rest, hover, pressed, keyboard-focus and disabled: hover steps the fill one surface level up (or to `accent-strong` for an accent-filled control), pressed holds that fill at slightly lower opacity, focus is the `focus-ring` shadow token (never an outline colour alone, since Windows keyboard users tab through this window constantly), and disabled drops to `surface-400` fill with `ink-tertiary` text and no hover step.

## Using this system

`tokens.json` is the only thing to read for values; `tokens.css` (generated) exposes each as a CSS custom property of the same name (`var(--accent)`, `var(--space-3)`…) and each type style as a class (`.body`, `.label`…). There is no component bundle: every `components/<Name>/preview.html` here is a small, self-contained HTML+CSS document built directly on those variables and classes, meant to be read as a reference and rebuilt in whatever the real window is written in (currently tkinter, per FR-13) — not executed as a library. Component guidelines below name the exact Uzbek strings and states each one needs; component names describe the piece (Button, StatusBadge, QueueRow…), not the tkinter widget it happens to be built from today.
