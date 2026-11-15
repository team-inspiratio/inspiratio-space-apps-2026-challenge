# 0016 Draft: comparison of website deployment options

> **This is a draft; a person decides.** This record deployed nothing and changed no access permissions or repository visibility.

## Background

The judges must be able to open the website, and keep being able to open it. According to the official schedule, the competition runs on 2026-11-14 and 15, judging follows, lists such as the Global Nominees are announced in December, and the Global Winners in January 2027 ([Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/)). So **the website must stay up reliably until at least January 2027**, not just through the competition weekend.

Current state (tested on 2026-11-04):

| Fact | Details |
|---|---|
| Live address | <https://inspiratio-fire-atlas.hybrid-0f7b5-5906.chatgpt.site> |
| Live version | The old version from before the fixes; `/methods.html` only falls back to the home page; PR #5 is not live |
| Access scope | `web/archive/website-v1/README.md` says "Sites private access", but the home page and data files open without logging in; **the two disagree, and a person must confirm** |
| Public source | `team-inspiratio/inspiratio-space-apps-2026-challenge`; current bundled assets are listed in `docs/public-data.md` |
| Members | 3 repository admins (terrywaio, QinqiXie, De1Ta-X), 1 with write access (qiuxue-yee) |
| Site size | The six-region `dist/` is about 44 MB. Adding the global version adds about 33 MB of front-end JSON (largest single file about 5 MB). The 663 MB `resamples20` is not suitable for a static site |
| Code | A static website, no server needed. There are 14 hard-coded root paths (such as `/data/v1/`, `/methods.html`), so the code must change to serve it under a subpath |

The competition terms require the team's original content to be freely available or under an open-source license ([Terms & Conditions](https://www.spaceappschallenge.org/legal/)), so the repository will most likely have to be public; that is decided separately (review packet X2).

## Comparison of options

Prices and limits in the table below were taken from the official pages on 2026-11-04; items marked "unverified" have no official statement we could find and **must be confirmed in the relevant dashboard before deciding**.

| | A Keep using chatgpt.site | B Vercel | C Netlify | D GitHub Pages (repository made public) |
|---|---|---|---|---|
| **Stability during judging** | Terms of service and retention unverified; depends on the publishing assistant and the project owner | Personal-project limits are clear; the Hobby deployment retention policy needs confirming (reports say a 30-day cap from 2026; unverified whether it affects the current production deployment) | The project may be paused once the 300 credits are used up (third-party claim, unverified); traffic risk during judging | Stays up as long as the repository exists; 100 GB/month is a soft limit, beyond which GitHub may get in touch |
| **Who can manage it** | Only the Sites project owner and those they authorize | Hobby has no team collaboration; essentially one person's account | Free and Personal allow few members; team collaboration needs Pro | All repository admins can manage it; deployment records are in Actions, visible to the whole team |
| **Works with a private repository?** | Yes, unrelated to GitHub (published by hand) | CLI upload of the build output works; conditions for connecting a private organization repository unverified | "Private organization repos" is listed under Pro; manual upload of the build output unverified | **No**. Free organizations support only public repositories; private needs the paid Team plan, and the published site itself is always public |
| **Cost** | The current arrangement; details unverified | Hobby is free (including 100 GB of transfer); Pro costs extra | Free: 300 credits/month; Pro from $20/month | Free |
| **Capacity** | The current 44 MB already works | CLI upload limit 100 MB (Hobby); with the global version about 77 MB, which fits but with little headroom | Each production deploy costs 15 credits, traffic 20 credits/GB | Site limit 1 GB, plenty |
| **Usage restrictions** | Unverified | Hobby is limited to non-commercial personal use; a competition project usually qualifies, **but whether an organization counts needs confirming** | No special restrictions | No special restrictions; the site is always public |
| **Code changes needed?** | No | No | No | **Yes**: served under the subpath `/inspiratio-space-apps-2026-challenge/`, the 14 root paths must be handled; an organization site repository avoids this (see below) |
| **Automatic publishing** | None; published by hand | Can connect to Git, or CLI by hand | Can connect to Git (private organization repositories need Pro), or by hand | Yes, automatically after merging into `main` |

## Steps

### A Keep using chatgpt.site

1. After PRs #4 and #5 are merged, someone with Sites access publishes following "Existing deployment and how to redeploy" in `web/archive/website-v1/README.md`.
2. Confirm in a private browsing window that the home page, `/methods.html` and the data files all open.
3. Confirm the access scope and update the README.

### B Vercel (CLI upload of the build output)

1. One team member signs up and confirms whether an organization project fits the Hobby terms.
2. Locally run `npm ci`, `npm run data:prepare`, `npm test`, `npm run build`.
3. Upload `web/archive/website-v1/dist` with the Vercel CLI and confirm the production address.
4. Confirm the deployment retention policy, so it is not cleaned up during judging.

### C Netlify (manual upload of the build output)

1. One team member signs up and confirms the new project is published as public (new projects are private by default).
2. As in step 2 of B, then upload `web/archive/website-v1/dist`.
3. Turn on usage alerts and estimate traffic during judging.

### D GitHub Pages

1. A person decides to make the repository public (X2), after first going through the history and the Release contents.
2. Handle the paths, choosing one of two ways:
   - Change the code: configure `base` in Vite, change the 14 root paths to relative paths, and open a PR that goes through the tests;
   - No code change: create a new public repository `team-inspiratio.github.io` containing only the build output, so the site is at the root path. This separates whether the source repository is public from the deployment.
3. Add a workflow: `npm ci` → `data:prepare` (Release fetched with `GITHUB_TOKEN`) → `npm test` → `npm run build` → publish to Pages.
4. In the repository's Settings → Pages, choose GitHub Actions. This step needs an admin.
5. Accept it in a private browsing window.

## Recommendation

**Do it in two steps, and don't move house on the competition weekend:**

1. **Now (before 11/13)**: after merging #4 and #5, first republish with **A**. It needs no code change and puts the fixed version online right away; it is also a step that is never wasted, whatever is chosen later.
2. **Once X2 decides to go public**: switch the judges' link to **D**, keeping A as a backup. Reasons:
   - judging continues until January 2027, and D does not depend on any one person's account or stop when credits run out;
   - any admin can fix it, and the publishing process is visible to the whole team;
   - it is free and has the most capacity;
   - the competition terms already lean toward public, and once public, D costs nothing extra.

**If it is decided not to go public**: keep using A and confirm it will stay up until January 2027. B and C both carry "single-person account" and "credits or terms" risks, and serve only as temporary backups.

**Before submitting to the judges**: whichever option is chosen, test it once in a private browsing window and once on a phone that has never logged in, and write the link into `docs/submission/checklist.md`.

## Status

**Awaiting human confirmation.** A person must decide: which option; whether the repository goes public (X2); and, if D, which path approach.

Unverified items a person must confirm: chatgpt.site's access scope, cost and retention; whether Vercel Hobby applies to organization projects, and deployment retention; how Netlify Free handles going over the limit.

## Sources

- GitHub: [What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- Vercel: [Hobby plan](https://vercel.com/docs/plans/hobby), [Limits](https://vercel.com/docs/limits), [Deployment protection](https://vercel.com/docs/deployment-protection)
- Netlify: [Pricing](https://www.netlify.com/pricing/)
