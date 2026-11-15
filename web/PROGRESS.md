# Frontend progress

Scope: C-line web application; the G-global data job and root PROGRESS.md remain with their existing owner.

## 2026-11-04

- Implemented region presets, map overlay, box/polygon/coordinate selections, calendar, direct-splice comparison, anomaly card, historical baseline selector and annual source curves.
- Implemented monthly CSV, selection GeoJSON and calendar PNG exports; method/validation and source/download dialogs.
- v1 inputs verified against the pinned Release manifest. Browser-only repackaging adds per-cell original counts and 20-draw arrays for custom selections without changing estimates.
- `npm test`: 36 passed, including all 25 repository anomaly cases and real data conservation across all six regions and 312 months.
- Browser checks: six region loads; correct observation-only holdout no-history state; California September 2020 = 125,460, above normal; a 64-full-cell custom box sums to 51 in October 2026; interactive mouse rectangle; 310-row CSV for 2001-01–2026-10; PNG; 390 px layout with no whole-page horizontal overflow.
- Build succeeds. Final repository CI and owner-private preview publication are recorded below when available.

## Remaining dependency

The raw-point CSV part of C5 requires approved region/year point assets that are absent from v1. The UI distinguishes monthly grid data from raw points. Global-v1 integration follows the released global interface after the data owner completes that job. Human usability testing on another physical device remains a follow-up.
