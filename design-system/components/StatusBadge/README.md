The one place colour ever names a queue item's state, and it always carries the Uzbek word with it — colour reinforces, the word decides. Five values, matching the spec's own vocabulary exactly (FR-13, section 9.1):

- `navbatda` — `muted` text on `muted-subtle`. Not started.
- `ishlanmoqda` — `accent` text on `accent-subtle`, with the live percentage appended ("Ishlanmoqda 42%"). The only state that also drives a ProgressBar.
- `tayyor` — `success` text on `success-subtle`. Finished; safe to open.
- `toʻxtatildi` — `muted` text on `muted-subtle`, same pair as `navbatda` (both mean "not currently happening"); told apart by the word alone, and by sitting next to a ProgressBar frozen mid-way rather than an empty one.
- `xato` — `danger` text on `danger-subtle`. `report.json`'s `skip_reasons` explains why underneath, in `caption`.

`label` type, `space-1` vertical / `space-2` horizontal padding, `radius-full`. A leading dot or glyph is optional and must repeat the pill's own colour — never a plain circle that could be mistaken for an unrelated indicator.
