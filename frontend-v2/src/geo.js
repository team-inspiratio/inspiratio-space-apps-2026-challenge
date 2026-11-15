export function longitudeParts(bounds) {
  const [west,south,east,north] = bounds;
  return west > east ? [[west,south,180,north],[-180,south,east,north]] : [bounds];
}

// Leaflet returns unwrapped longitudes when panning across the date line.
export function drawnBounds(a,b) {
  const west=Math.min(a.lng,b.lng),east=Math.max(a.lng,b.lng);
  const wrap=x=>((x+180)%360+360)%360-180;
  return [east-west>=360?-180:wrap(west),Math.max(-85,Math.min(a.lat,b.lat)),east-west>=360?180:wrap(east),Math.min(85,Math.max(a.lat,b.lat))];
}

export function cellInBounds(lat,lon,bounds) {
  return longitudeParts(bounds).some(([w,s,e,n])=>lon < e && lon+.25 > w && lat < n && lat+.25 > s);
}

// Find the shortest circular longitude span, so islands on both sides of 180 stay adjacent.
export function gridExtent(cells) {
  if (!cells.length) return null;
  const lons = [...new Set(cells.map(c=>c.lon))].sort((a,b)=>a-b);
  let gap=-1, start=lons[0];
  for(let i=0;i<lons.length;i++) {
    const next=i+1<lons.length ? lons[i+1] : lons[0]+360;
    if(next-lons[i]>gap) { gap=next-lons[i]; start=next%360; if(start>180)start-=360; }
  }
  let south=90,north=-90,east=start;
  for(const c of cells) {
    south=Math.min(south,c.lat); north=Math.max(north,c.lat+.25);
    east=Math.max(east,c.lon+(c.lon<start?360:0)+.25);
  }
  return [[Math.max(-85,south),start],[Math.min(85,north),east]];
}

// Camera framing only: keep the central 98% of detection weight on each axis.
// Outlying cells remain rendered and remain included in every regional statistic.
export function activityExtent(cells) {
  const active=cells.filter(c=>c.value>0);
  if(!active.length)return gridExtent(cells);
  const west=gridExtent(active)[0][1];
  const points=active.map(c=>({...c,x:c.lon<west?c.lon+360:c.lon}));
  const total=points.reduce((s,c)=>s+c.value,0);
  const quantile=(axis,q)=>{
    let sum=0;
    for(const c of [...points].sort((a,b)=>a[axis]-b[axis])) {
      sum+=c.value;if(sum>=total*q)return c[axis];
    }
  };
  const w=quantile('x',.01),e=quantile('x',.99),s=quantile('lat',.01),n=quantile('lat',.99);
  return [[Math.max(-85,s),w],[Math.min(85,n+.25),e+.25]];
}
