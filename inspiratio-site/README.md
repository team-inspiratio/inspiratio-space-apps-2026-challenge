# Inspiratio Site

This is a standalone snapshot of the Svelte / Vite website. The `archive/` and `website/` directories in the main repository are other versions.

## Running locally

Run the following commands from this directory.

```sh
npm ci
npm run dev -- --port 5199
```

Open [localhost:5199](http://localhost:5199). Run `npm test` for unit tests, `npm run check` for type checking, and `npm run build` to generate `dist/`.

The site reads the assets shipped in `public/`. The monthly data and fire grid come from Inspiratio `global-v1` (CC BY 4.0), built on NASA FIRMS MODIS and VIIRS active fire data. Map geography comes from Natural Earth. See the [global data interface](../docs/data-interface-global.md) for data definitions.

## Handoff materials

- [Revision prompt and the two original screenshots](revision-handoff/)
- [Previous handoff summary](revision-handoff/PRIOR-STATUS.md)
- [Existing demo recording](out/scroll-desktop.mp4) and [review screenshots](review/)
