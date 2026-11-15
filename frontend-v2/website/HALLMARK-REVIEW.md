# V2 design review

Status: owner approved merging this design into main after removing punctuation from the two editorial headings. Public hosting is managed separately.

## Direction

Use Hallmark 2.0.0 as an app restyle with the existing DESIGN.md brand system. The visual signature remains the real geographic activity grid and full monthly calendar. Cool paper, dark ink, serif editorial headings and flat ruled sections replace competing borders and small low-contrast labels. System fonts keep rendering independent of font downloads. No decorative imagery or fabricated evidence is introduced.

## Preserved behavior and content

Only a stylesheet import and the owner-requested heading punctuation change in main.js. Data loading, mapping, coordinate selection, drawing, date-line handling, calculations, calendar interaction, CSV/PNG exports, sharing and accessibility controls retain their existing implementation. All scientific files and the original web/ site remain untouched. A noscript message explains the existing JavaScript requirement.

The content comparison retained 7/7 links, 15/15 fields, 9/9 headings and 59/59 figures. Existing copy and metadata remain intact, except for the owner-requested removal of periods from the two editorial headings. The sequential red activity scale remains the default, with existing opt-in assistance palettes.

## Verification

- Hallmark source and rendered audit: 0 FAIL, 0 REFLEX, 0 WARN across five stylesheets and the local app.
- Rendered widths: 375, 1280, 1440 and 1920 pixels.
- Existing unit suite: 37 tests passed.
- Existing browser suite passed: real release values, baseline and region changes, reload, CSV/PNG export, keyboard operation and mobile layout.
- Production build passed.
- Scientific guardrails checked separately before commit.

Finish review was performed in-thread, not by an independent reviewer. The desktop hierarchy and mobile evidence layout were inspected; mobile overflow and several low-contrast labels were corrected. No new action, heading or figure was removed. The old dense table remains horizontally scrollable on narrow screens so all twelve months stay available without shrinking touch targets.

## Review limits

The automated audit is not a full accessibility certification. Existing map tiles require network access. Existing source/data limitations and uncertainty explanations are preserved. The review draft does not update the public deployment. No additional photography or brand material is needed for this data application.
