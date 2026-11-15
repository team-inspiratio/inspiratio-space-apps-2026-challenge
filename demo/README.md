# Fire Atlas — 30-second demo, first cut

- Video: `output/fire-atlas-demo-v1.mp4`
- Contact sheet: `output/storyboard.jpg`
- Browser player: `output/preview.html`
- Reproducible animation source: `scripts/render.py`
- Assets: `assets/` (captured real website, cropped UI, original report figures). The music track is not included in this repository; to re-render, place it at `assets/music-original.mp3`.

1920×1080, 30 fps, 30 seconds. No voice-over. English on-screen story.
The audio uses 0:00–0:30 of the supplied track, with short fades. This is a local review cut, not a published submission.

## Shot list

| Seconds | Content |
|---|---|
| 0–5 | Southern Africa sensor difference: approximately five times as many detections; sensor reveal |
| 5–10 | Fire Atlas; overlap learning; 2000-11 to 2026-10 |
| 10–15 | Actual Chongqing study-area map, August 2022, approximately 420 detections |
| 15–21 | Actual monthly calendar; 6.8× historical August median |
| 21–25.5 | Global validation: MALE 0.619 to 0.534, approximately 14% lower |
| 25.5–30 | Intended use, team, challenge, music and data credits |

## Evidence and provenance

Repository root: `../` (paths below are relative to it).

- Hook: `reports/validation.md`, summary and Figure 1 caption. Southern Africa annual S-NPP/Aqua ratio 4.8–5.6 in 2014–2021. Animated bars are an explicitly labeled approximate ratio, not invented annual measurements.
- Dates/resolution: `README.md`, `docs/data-card.md`: 312 months, 0.25-degree cells.
- Method: `harmonization/README.md`, `docs/submission/project-page.md`. Two-stage LightGBM; historical MODIS inputs, S-NPP reference scale.
- Chongqing: `website/REVIEW.md`. Box [106,29,108,30.5], 48 cells, August 2022 420.03, historical August median 62, 21 reference years, ratio 6.7747, scaled NOAA-20. Actual published UI independently displayed approximately 420 and 6.77× during capture.
- Calendar and map: captured from https://inspiratio-fire-activity-v2.hushedotter14.chatgpt.site/ on 2026-11-15, with the above study box selected. No website data modified. Product visuals are screenshot-based camera animation, not a continuous screen recording. Map labels retain the provider language.
- Global validation: `reports/global-scores.md`, two-window MALE 0.534 (global refit) vs 0.619 (M1s). Relative reduction 13.73%, rounded to 14%. This is not accuracy and not a blind test.
- Regional blind-test context: `reports/final-test.md`: 22% and 25% relative MALE reductions, separate from global-model validation.
- Names: user-provided team screenshot. Capitalization normalized for Xinrui Zhou only.

## Credits

Music: MoFeansy / Warsic — "Xi Jian", from the album "Jing Yu Ni". Supplied by the user; file metadata provides the attribution. Music authorization has not been verified. Attribution is included in the video, but does not establish permission to publicly distribute it.

Satellite data: NASA FIRMS. Map: © OpenStreetMap contributors (https://www.openstreetmap.org/copyright), Natural Earth; Leaflet. No NASA logo or team-member portraits used.

Animation and editing: programmatic Python/Pillow and FFmpeg assisted by Codex; disclose this in the submission's SI section as appropriate.

## Re-render

Requires Python with Pillow, FFmpeg, and the macOS Arial/Georgia fonts. In this session:

```sh
/tmp/fire-demo-venv/bin/python demo/scripts/render.py
```

`--stills` regenerates only the storyboard and selected frames. Source scientific files and website source are unchanged.

## V2 revision

Video: `output/fire-atlas-demo-v2.mp4`. V1 is retained for comparison.

Timeline: 0–4 sensor gap; 4–7 method; 7–12 before/after published period averages; 12–15 actual map; 15–19 actual calendar; 19–26 preregistration / freeze / blind-test evidence plus separate global validation; 26–30 credits and intended use.

Added chart uses `reports/validation.json`, `fig5_series.southern_africa`: direct-splice mean annual 2003–2011 = 249481.6667; harmonized mean annual 2003–2011 = 1246069.7717; 2014–2021 observed mean = 1224269.0. These are period averages, explicitly not an accuracy test or a full time series.

Audio: V1 measured integrated -19.12 LUFS, true peak -2.81 dBTP. V2 applies a fixed -6 dB gain, retaining musical dynamics and existing fades. Quieter background target is editorial, not an official NASA or universal platform requirement.
