// Pieces shared by the atlas page and the method page.
export const REPO =
  "https://github.com/team-inspiratio/inspiratio-space-apps-2026-challenge";

const icons = {
  arrow: "M7 17 17 7M7 7h10v10",
  download: "M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5",
  map: "m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Zm6-3v15m6-12v15",
  box: "M4 4h16v16H4z",
  polygon: "m5 5 13-2 3 13-11 5-7-9Z",
  info: "M12 11v6m0-10v.1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  chevron: "m9 5 7 7-7 7",
  reset: "M3 10a9 9 0 1 1 1 8M3 3v7h7",
  close: "m6 6 12 12M6 18 18 6",
  clock: "M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  check: "m5 12 4 4L19 6",
  spark: "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
};
export const icon = (name, cls = "") =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.info}"/></svg>`;

/** Site header. On the atlas, "Data & sources" opens the downloads dialog; elsewhere it links back to it. */
export const siteHeader = (page) =>
  `<header class="site-header"><a class="brand" href="/" aria-label="Inspiratio Fire Atlas home"><img src="/favicon.svg" alt=""/><span>inspiratio<span class="brand-divider">/</span><strong>Fire Atlas</strong></span></a>
    <nav aria-label="Main navigation"><a class="nav-link ${page === "atlas" ? "active" : ""}" href="/#explore" ${page === "atlas" ? 'aria-current="page"' : ""}>Explore</a><a class="nav-link ${page === "methods" ? "active" : ""}" href="/methods.html" ${page === "methods" ? 'aria-current="page"' : ""}>Method & validation</a>${page === "atlas" ? `<button class="nav-link" data-downloads>Data & sources ${icon("arrow")}</button>` : `<a class="nav-link" href="/#data">Data & sources ${icon("arrow")}</a>`}</nav>
    <span class="header-note"><span class="status-dot"></span>NASA Space Apps 2026</span></header>`;

/** Fetch a published .gz asset, decompressing in the browser when the server did not. */
export async function gzipBytes(url) {
  const r = await fetch(url);
  if (!r.ok)
    throw Error(
      "Could not load published data (" + r.status + "). Please retry.",
    );
  const bytes = new Uint8Array(await r.arrayBuffer());
  if (bytes[0] === 31 && bytes[1] === 139) {
    if (!window.DecompressionStream)
      throw Error(
        "This browser does not support gzip decompression. Please use a current browser.",
      );
    return new Uint8Array(
      await new Response(
        new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")),
      ).arrayBuffer(),
    );
  }
  return bytes; // Also supports servers that decode Content-Encoding automatically.
}
