# Pre-submission checklist

> **Draft. Check item by item after the official guides are released on 11/13.** The Project Submission Guide and the Judging & Awards Guide are both released on November 13; the requirements below come from the 2026 FAQ, the participant terms and `docs/proposal.md` (2025 rules), and the official guides prevail once out.
>
> Sources: [Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/), [Terms & Conditions](https://www.spaceappschallenge.org/legal/) (read on 2026-11-04).

## 1. Prerequisites to settle first

- [ ] Confirm whether the team registered for a Local Event or the Universal Event. The proposal says Universal; the two have different contacts and deadlines
- [ ] Group A of the review packet has been signed off

## 2. Eligibility

- [ ] Everyone has registered on spaceappschallenge.org and accepted the terms (registration is open until the competition ends on November 15)
- [ ] The team has at most 6 members; a Universal Event team needs at least 2 to be eligible for global judging
- [ ] Each person is in only one team, and the team works on only one challenge
- [ ] Everyone is under the same event
- [ ] If any team member is under 18: no photos, video or voice may be used, and per the FAQ a guardian registers and accompanies them

## 3. Code, data, licenses

- [ ] The code repository is public and opens for judges without logging in (currently private; review packet X2)
- [ ] Before going public, a person checked the history and the Release contents, and the gitleaks CI passes
- [ ] A code license has been added and meets the OSI open-source definition (the repository currently has no LICENSE file)
- [ ] The datasets Release v1 / global-v1 are publicly downloadable, CC BY 4.0
- [ ] All non-NASA materials have been confirmed as publicly usable, with licenses stated in the submission documents: GFED4.1s, OpenStreetMap basemap, Natural Earth, LightGBM, Leaflet, leaflet-draw, Turf, topojson-client, world-atlas, Vite, hyparquet
- [ ] **Every source has been cited**, including open-source software. The terms state that failing to cite may lead to removal or revocation of awards
- [ ] The FIRMS acknowledgment has been put on the project page
- [ ] Confirmed the work contains no export-controlled information (the terms make the team responsible for this)

## 4. Website

- V2 GitHub Pages address: <https://team-inspiratio.github.io/inspiratio-space-apps-2026-challenge/>. Deployment and automated checks are recorded in the `Deploy V2 to GitHub Pages` workflow.

- [ ] PRs #4 and #5 are merged and the fixed version is deployed (ADR 0016)
- [ ] In a private browsing window, the home page and `/methods.html` both open and neither is the old version
- [ ] Tested again on a phone that has never logged in
- [ ] The code and report links on the methods page open once the repository is public
- [ ] Confirmed the website will stay up until after the winners are announced in January 2027
- [ ] The web page uses only published data and does not change numbers on the front end

## 5. Project page

- [ ] Every bracketed item in `project-page.md` has been handled
- [ ] The numbers in the text have been checked against `reports/` once more, and the closing "Where the numbers come from" section has been deleted
- [ ] No wording such as accuracy, error bar, forecast or burned area anywhere in the text
- [ ] The blind-test scores and the global validation scores are written separately, stating clearly that the global version had no blind test
- [ ] The limitations outside the training regions are in the main text, not a footnote
- [ ] The SI usage statement is written, including the tools used for video and images (required by the organizers for every project)
- [ ] Third-party content is used in line with the [brand guidelines](https://www.spaceappschallenge.org/brand/), with no unauthorized use of the NASA logo
- [ ] At least one teammate has read the whole text

## 6. Demo

- [ ] The video length and format meet the official guide (for now: 30 seconds, English captions)
- [ ] Or the slides meet the official guide (for now: at most 7 pages, all in English)
- [ ] Recorded on the fixed website
- [ ] The video was made by the team itself, and no material infringes copyright (required by the terms)
- [ ] The public link plays in a private browsing window

## 7. Submission

- [ ] Submit in the Project tab of the team page; this is the only way into global judging
- [ ] All required fields are filled in
- [ ] Confirm the event's deadline. The proposal records it as opening at 9:00 on November 14 and closing at 23:59 on November 15 (local event time); the FAQ says it follows the end time of the chosen event
- [ ] Submit at least a few hours early to leave time for changes
- [ ] Save a screenshot of the confirmation page

## 8. To check on the day the guides are released (11/13)

- [ ] The 2026 judging criteria and awards (the proposal used the 2025 version)
- [ ] Video length and format, number of slides
- [ ] Required fields and word limits
- [ ] Specific requirements for the AI (SI) statement
- [ ] Whether the challenge resources (released on November 13) contain new data or requirements
