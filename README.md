# MODIS × VIIRS Hotspot Harmonization

We turn the hotspot records of two satellite sensor generations, MODIS (from 2000) and VIIRS (from 2012), into one monthly series that can be compared across the whole period, then build a web page where people pick an area, view its history, judge whether the latest complete month is unusually high, and download the results.

**Full proposal: [docs/proposal.md](docs/proposal.md)**

## The one-minute version

- **Problem:** The two sensors differ in resolution and sensitivity, and VIIRS records clearly more hotspots. Stitched together directly, the series shows a jump in 2012 that is caused by the change of satellite, not by a change in fire activity.
- **Approach:** Train a model on the years when both sensors were in orbit to predict, from MODIS information alone, how many hotspots VIIRS would record, then apply this conversion to the years before 2012. The main model is LightGBM, with a simple ratio method as the baseline for comparison; an AI-driven automated experiment loop helps improve the model on the validation set.
- **Validation:** Use later years to predict earlier years, and hold out one region the model has never seen. The validation set selects the model; the test set stays locked, is run only once after the model is frozen, and is reported as it comes out.
- **Outputs:** A harmonization algorithm, a public dataset and a web page, plus a write-up of the methods and validation.

## Proposal contents

| Part | Contents |
|---|---|
| [Project overview](docs/proposal.md#project-overview) | Problem, solution, deliverables |
| [In plain language](docs/proposal.md#in-plain-language-what-this-project-does) | An explanation that needs no remote-sensing background |
| [Approach](docs/proposal.md#approach-using-machine-learning-to-bring-history-onto-the-viirs-scale) / [Validation](docs/proposal.md#validation-how-we-show-the-model-can-be-trusted) | The core of the main proposal |
| [Web page](docs/proposal.md#what-the-web-page-delivers) / [Implementation scope](docs/proposal.md#implementation-scope) | What users can do; required work and extensions |
| [Appendix: Execution handbook](docs/proposal.md#appendix-execution-handbook) | Data, algorithm, validation framework, AI loop, 24 tasks, submission materials, risks, references |

## Repository layout

```
README.md          This file
docs/proposal.md   Full proposal (main proposal + execution handbook)
notes/             Reading and study notes
requirements.txt   Python dependencies
.env.example       Secrets template (copy to .env; .env is never committed)
```

## Conventions

- Changes go through branches and pull requests; do not push directly to main.
- Secrets (such as the FIRMS MAP_KEY) live only in a local `.env`.
- Raw data and large processed files stay out of the repository; their sources and download steps are documented.
