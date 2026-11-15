# A common Earth record

Purpose: let a reader choose a place, compare monthly fire-detection activity on one sensor scale, understand an unusual month, and export traceable results. Detections are not individual fires, burned area, risk or predictions.

Design is independent of the original frontend. Read sources: proposal, execution plan, data interfaces, data card, scientific anomaly reference, validation reports. The Hallmark restyle lives only in frontend-v2/ on design/v2-hallmark, approved by the owner for merging after removing punctuation from the two editorial headings.

Palette: ocean #dfeef3, ink #173948, paper #f8fbfc, land #becfce, fire #e56543, teal #287b79. Fire color encodes activity; blue-green provides geographic context. Type: locally available Segoe UI / system sans for controls and Georgia for editorial headings. No remote fonts. Existing Leaflet basemap tiles and attribution are preserved.

Hallmark direction: a restrained research atlas, using the existing brand rather than a replacement theme. Cap the main container at 1440px; use aligned rules, flat paper surfaces, square controls and generous section spacing. Keep control typography familiar and the map/calendar dominant. Preserve English copy, dataset values, scientific statements, source links and all application wiring. Default activity colors remain sequential red; accessible alternatives remain opt-in. CSS tokens hold the palette, typography and shared spacing. The design overlay is src/hallmark.css.

Layout: a quiet horizontal navigation, compact purpose statement, geographic workspace beside a month inspector; a wide calendar and historical comparison below. Align text left. A map of the actual Earth is the defining visual, with no decorative fake fire points. On mobile the inspector follows the map and the calendar scrolls horizontally.

Review against brief: use actual geographical outlines and discrete month cells, rather than dashboard KPI tiles or a generic marketing hero. Distinguish data source and uncertainty at the point of use. Use English throughout, as requested by the user. Exports carry version, source, coverage and near-real-time flags. Full released data load on demand; the honest offline fallback contains four real same-month series from the scientific contract, not invented full-year data.

Design reference: https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md (read during implementation). No original frontend source or assets used.
