<script lang="ts">
  import { AS_OF } from '../lib/store.svelte'
  const REPO = 'https://github.com/team-inspiratio/inspiratio-space-apps-2026'
  const data = [
    {
      name: 'MODIS Collection 6.1 Active Fire, Terra and Aqua',
      res: '1 km · Nov 2000 onward',
      use: 'The only record before 2012; the model input for every estimated month.',
      href: 'https://firms.modaps.eosdis.nasa.gov/download/',
    },
    {
      name: 'VIIRS 375 m Active Fire, Suomi NPP',
      res: '375 m · Jan 2012 to 2 Nov 2026',
      use: 'The target scale. Observed values from 2014; 2012–13 were the sealed test.',
      href: 'https://firms.modaps.eosdis.nasa.gov/download/',
    },
    {
      name: 'VIIRS 375 m Active Fire, NOAA-20',
      res: '375 m · Apr 2018 onward',
      use: 'Fills S-NPP gaps, scaled to S-NPP; continues the record after S-NPP.',
      href: 'https://firms.modaps.eosdis.nasa.gov/download/',
    },
  ]
</script>

<footer class="foot" id="about">
  <div class="cols">
    <section>
      <h2>NASA data used</h2>
      <ul class="data">
        {#each data as d}
          <li>
            <a href={d.href} target="_blank" rel="noreferrer">{d.name}</a>
            <span class="faint small">{d.res}</span>
            <span class="muted small">{d.use}</span>
          </li>
        {/each}
      </ul>
      <p class="small muted">
        All via NASA FIRMS (Fire Information for Resource Management System). Regions follow the GFED4.1s basis regions.
      </p>
    </section>
    <section>
      <h2>Data and code</h2>
      <ul class="plain small">
        <li><a href="{REPO}/releases/tag/global-v1" target="_blank" rel="noreferrer">Dataset release global-v1</a> <span class="faint">· CC BY 4.0 · monthly, 0.25°, Nov 2000 – Oct 2026</span></li>
        <li><a href={REPO} target="_blank" rel="noreferrer">Source code and reports</a> <span class="faint">· validation, final test, decisions</span></li>
        <li class="muted">Reproducible: one command rebuilds the dataset from the FIRMS archives in about 87 minutes, and 37 checks match bit for bit.</li>
        <li class="muted">Values are monthly counts of fire detections at VIIRS S-NPP 375 m scale. They are not fire events, burned area or fire danger.</li>
      </ul>
    </section>
    <section>
      <h2>How AI was used</h2>
      <p class="small muted">
        The data pipeline, models, validation and this site were written with AI coding assistants (Claude Code), under human
        review. People chose the holdout regions, reviewed the grading code before it was frozen, and triggered the one-time blind
        test. Every AI-assisted commit is marked in the repository. Details: docs/ai-usage.md.
      </p>
      <h2 class="team">Team Inspiratio</h2>
      <p class="small muted">NASA Space Apps Challenge 2026. Readings use data available as of {AS_OF}.</p>
    </section>
  </div>
</footer>

<style>
  .foot { position: relative; z-index: 3; background: var(--panel); border-top: 1px solid var(--rule); padding: 56px 32px 64px; }
  .cols { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 48px; max-width: 1400px; }
  h2 { font-size: 15px; margin-bottom: 14px; }
  h2.team { margin-top: 24px; margin-bottom: 6px; }
  ul { list-style: none; margin: 0 0 14px; padding: 0; display: grid; gap: 12px; }
  .data li { display: grid; gap: 1px; }
  .data a { font-weight: 600; text-decoration: none; }
  .data a:hover { text-decoration: underline; }
  .plain { gap: 10px; }
  @media (max-width: 899px) {
    .cols { grid-template-columns: 1fr; gap: 32px; }
    .foot { padding: 40px 20px; }
  }
</style>
