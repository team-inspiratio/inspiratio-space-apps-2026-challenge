import { longitudeParts, cellInBounds } from './geo.js';
import { subset, validateBounds } from './science.js';

export function intersects(a,b) {
  return longitudeParts(a).some(([w,s,e,n])=>longitudeParts(b).some(([x,y,z,t])=>w<z&&e>x&&s<t&&n>y));
}

// Global region files partition the grid; demonstration box files overlap them.
export function areaCandidates(items,bbox) {
  validateBounds(bbox);
  const partitioned=items.some(x=>x.kind==='region');
  return items.filter(x=>(partitioned?x.kind==='region':x.kind!=='box')&&intersects(x.bbox,bbox));
}

export function createAreaCollector(bbox) {
  validateBounds(bbox);
  let months;
  const rows=[], contributors=[], seen=new Set();
  return {
    add(region) {
      const d=region.rawData;
      if(!months)months=d.months;
      if(JSON.stringify(months)!==JSON.stringify(d.months))throw Error('Regional time axes do not match. No custom total was created.');
      let added=0;
      for(let i=0;i<d.cells.lat_idx.length;i++) {
        const lat=d.cells.lat_idx[i],lon=d.cells.lon_idx[i];
        if(!cellInBounds(lat*.25-90,lon*.25-180,bbox))continue;
        const key=`${lat},${lon}`;
        if(seen.has(key))throw Error('Overlapping release partitions found. No custom total was created.');
        seen.add(key);added++;
        rows.push({lat,lon,est:d.est[i],sources:d.month_source});
      }
      if(added)contributors.push({name:region.name,label:region.label,role:region.role,data:{month_source:d.month_source,month_nrt:d.month_nrt,month_input_complete:d.month_input_complete}});
    },
    finish() {
      if(!rows.length)throw Error('No released grid cells overlap this area. Try a nearby land area or a larger rectangle.');
      const data={months,cells:{lat_idx:rows.map(r=>r.lat),lon_idx:rows.map(r=>r.lon)},est:rows.map(r=>r.est),cell_sources:rows.map(r=>r.sources),
        totals:{est:months.map(()=>null)},
        month_source:months.map((_,t)=>{const types=[...new Set(contributors.map(c=>c.data.month_source[t]))];return types.length===1?types[0]:'mixed';}),
        month_nrt:months.map((_,t)=>contributors.some(c=>c.data.month_nrt[t])),
        month_input_complete:months.map((_,t)=>contributors.every(c=>c.data.month_input_complete[t]===true))};
      return {bbox,data,series:subset(data,bbox),regions:contributors.map(({name,label,role})=>({name,label,role})),cellCount:rows.length};
    }
  };
}
