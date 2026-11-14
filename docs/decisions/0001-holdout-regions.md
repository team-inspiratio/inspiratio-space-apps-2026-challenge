# 0001 Choice of holdout regions

## Background

Section 2 of the execution plan requires that the holdout regions used for Test 2 (spatial extrapolation) be registered in advance, before any VIIRS data is touched. The plan suggests 3 regions but says "needs team confirmation". S01 in session 1 has to write the holdout regions into `config/regions.json` and freeze them, so they need to be confirmed first.

## Options

1. **The 3 regions suggested in the plan**: northern Australia, central Siberia and India's Ganges Plain, each about 10°×10°.
2. **Only the 1 region originally set in the proposal** (northern Australia): less data, but it can test only one type of fire.
3. **Choose other regions**: needs a new justification, and the choice may not be based on VIIRS data.

## Recommendation

Option 1. The three regions each stand for a different type of fire:

| Holdout region | Fire type | Notes |
|---|---|---|
| Northern Australia | Savanna fires | Originally set in the proposal; lies within 30°S, the latitude band where the MODIS orbital gaps are most pronounced |
| Central Siberia | Boreal forest fires | High latitude; existing research shows that in large boreal forest fires the difference between the two sensors is not the same as in other ecosystems |
| India's Ganges Plain | Crop-residue burning | Many small fires, concentrated in a few seasons; the best test of how well the model infers the small fires MODIS cannot see |

This way Test 2 can show whether the model still works in regions it has not seen and on different types of fire, which is more convincing than using a single region.

## Status

**Confirmed: the user, 2026-11-03.** The user's words (translated from Chinese): "No objections, then. Just add it to GitHub directly, as long as nothing's wrong with it."

## Implementation rules (S01 follows these without asking anyone again)

- Each region is a latitude/longitude rectangle of about 10°×10°. When S01 writes `config/regions.json`, the exact bounds are set only from geographic location and ecosystem type, **without looking at any VIIRS data**, and are then frozen.
- The holdout regions must not overlap the training and showcase regions (California, Córdoba in Argentina, the southern African savanna).
- VIIRS records in the holdout regions are dropped during import in S03 and never written to disk (plan section 4).

## Related decisions

On the same day the user also confirmed: extend to global coverage (stage G changes from optional to planned), and keep the main product on the VIIRS scale. See section 2 of the execution plan.
