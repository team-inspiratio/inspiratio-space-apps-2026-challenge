import context from "./context.json";
import { releaseSeries } from "./science.js";
import { areaCandidates, createAreaCollector } from './area.js';
export const names = {
  california: "California",
  cordoba: "Córdoba",
  southern_africa: "Southern Africa",
  north_australia: "Northern Australia",
  central_siberia: "Central Siberia",
  indo_gangetic: "Indo-Gangetic Plain",
  BONA: "Boreal North America",
  TENA: "Temperate North America",
  CEAM: "Central America",
  NHSA: "Northern South America",
  SHSA: "Southern South America",
  EURO: "Europe",
  MIDE: "Middle East",
  NHAF: "Northern Africa",
  SHAF: "Southern Africa (GFED)",
  BOAS: "Boreal Asia",
  CEAS: "Central Asia",
  SEAS: "Southeast Asia",
  EQAS: "Equatorial Asia",
  AUST: "Australia & New Zealand",
};
export const evidence = context;
const cache = new Map();
export async function catalog() {
  try {
    const response = await fetch(
      import.meta.env.BASE_URL + "data/global-v1/ready.json",
    );
    if (!response.ok) throw Error();
    await response.json();
    const r = await fetch(
      import.meta.env.BASE_URL + "data/global-v1/index.json",
    );
    if (!r.ok) throw Error();
    const body = await r.json();
    const items = Array.isArray(body)
      ? body
      : (body.units ?? body.regions ?? body.files);
    if (!Array.isArray(items) || !items.length) throw Error();
    return {
      sample: false,
      items: items.map((x) => ({
        ...x,
        label: names[x.name] ?? x.label,
        version: "global-v1",
      })),
    };
  } catch {
    return {
      sample: true,
      items: context.examples.map((x) => ({
        ...x,
        label: names[x.name],
        bbox: [x.west, x.south, x.east, x.north],
      })),
    };
  }
}
export async function loadRegion(item) {
  if (item.sample) return item;
  if (cache.has(item.name)) return cache.get(item.name);
  const r = await fetch(
    import.meta.env.BASE_URL + "data/global-v1/" + item.file.split("/").pop(),
  );
  if (!r.ok) throw Error("Data for this region are unavailable. Please retry.");
  const bytes = new Uint8Array(await r.arrayBuffer());
  // Some hosts transparently decompress .gz responses. Inspect bytes, not suffixes.
  const text = bytes[0] === 31 && bytes[1] === 139
    ? await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).text()
    : new TextDecoder().decode(bytes);
  const d = JSON.parse(text);
  const result = {
    ...item,
    series: releaseSeries(d),
    rawData: d,
    target: d.months.at(-1),
  };
  cache.set(item.name, result);
  if (cache.size > 2) cache.delete(cache.keys().next().value);
  return result;
}

export async function loadArea(items,bbox,onProgress=()=>{},isCurrent=()=>true) {
  const candidates=areaCandidates(items,bbox),collector=createAreaCollector(bbox);
  for(let i=0;i<candidates.length;i++) {
    if(!isCurrent())return null;
    onProgress(`Loading area coverage ${i+1}/${candidates.length}…`);
    collector.add(await loadRegion(candidates[i]));
  }
  return isCurrent()?collector.finish():null;
}
