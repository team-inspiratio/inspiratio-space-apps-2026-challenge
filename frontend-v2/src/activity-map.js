import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { feature } from "topojson-client";
import world from "world-atlas/countries-110m.json";
import { gridExtent, activityExtent, cellInBounds, longitudeParts, drawnBounds } from "./geo.js";
import { sourceLabel } from './science.js';

export function createActivityMap(element, onRead, onSelect, onMode=()=>{}) {
  const map=L.map(element,{scrollWheelZoom:true,preferCanvas:true,minZoom:1,maxZoom:15,zoomControl:false,zoomAnimation:false}).setView([20,0],2);
  map.createPane('outlines');map.getPane('outlines').style.zIndex=190;
  // Geographic outlines remain available when internet tiles are unavailable.
  L.geoJSON(feature(world,world.objects.countries),{pane:'outlines',interactive:false,style:{color:'#b4c8d0',weight:.7,fillColor:'#d8e3e5',fillOpacity:1}}).addTo(map);
  const tile=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
  tile.on('tileerror',()=>{element.dataset.tiles='unavailable';});
  tile.on('tileload',()=>{element.dataset.tiles='available';});
  map.attributionControl.addAttribution('Natural Earth · NASA FIRMS');
  L.control.scale({imperial:false}).addTo(map);
  map.on('moveend zoomend',()=>{element.dataset.zoom=map.getZoom();element.dataset.center=map.getCenter().toString();});
  let cells=[], bounds=null, color, currentMonth='', max=1, lookup=new Map(), lastKey='';
  const Canvas=L.Layer.extend({
    onAdd(){this.canvas=L.DomUtil.create('canvas','fire-canvas',map.getPanes().overlayPane);map.on('moveend zoomend resize',this.draw,this);this.draw();},
    onRemove(){map.off('moveend zoomend resize',this.draw,this);this.canvas.remove();},
    draw(){
      const size=map.getSize(),dpr=window.devicePixelRatio||1,c=this.canvas;
      L.DomUtil.setPosition(c,map.containerPointToLayerPoint([0,0]));
      c.width=size.x*dpr;c.height=size.y*dpr;c.style.width=size.x+'px';c.style.height=size.y+'px';
      const ctx=c.getContext('2d');ctx.scale(dpr,dpr);
      const center=map.getCenter().lng;
      for(const cell of cells) {
        if(bounds&&!cellInBounds(cell.lat,cell.lon,bounds))continue;
        const pieces=bounds?longitudeParts(bounds):[[-180,-90,180,90]];
        for(const [w,s,e,n] of pieces) {
        const west=Math.max(w,cell.lon),east=Math.min(e,cell.lon+.25),south=Math.max(s,cell.lat),north=Math.min(n,cell.lat+.25);
        if(west>=east||south>=north)continue;
        const shifted=west+360*Math.round((center-west)/360);
        for(const lon of [shifted-360,shifted,shifted+360]) {
          const a=map.latLngToContainerPoint([Math.min(85,north),lon]);
          const b=map.latLngToContainerPoint([Math.max(-85,south),lon+east-west]);
          if(b.x<0||a.x>size.x||b.y<0||a.y>size.y||cell.lat>=85||cell.lat+.25<=-85)continue;
          ctx.fillStyle=cell.value===0?'rgba(75,96,105,.12)':color(cell.value,max);
          ctx.fillRect(a.x,a.y,Math.max(.4,b.x-a.x),Math.max(.4,b.y-a.y));
        }
        }
      }
    }
  });
  const layer=new Canvas().addTo(map), selection=L.featureGroup().addTo(map);
  let drawing=false,anchor=null,preview=null,pointer=null;
  function setDrawing(enabled) {
    drawing=enabled;anchor=null;
    if(preview){preview.remove();preview=null;}
    element.classList.toggle('drawing-area',enabled);
    if(enabled){map.dragging.disable();map.scrollWheelZoom.disable();map.doubleClickZoom.disable();}
    else {map.dragging.enable();map.scrollWheelZoom.enable();map.doubleClickZoom.enable();}
    onMode(enabled);
  }
  element.addEventListener('pointerdown',event=>{
    if(!drawing||event.button!==0||event.target.closest('.leaflet-control'))return;
    event.preventDefault();event.stopPropagation();
    pointer=event.pointerId;element.setPointerCapture(pointer);
    anchor={latlng:map.mouseEventToLatLng(event),point:map.mouseEventToContainerPoint(event)};
    preview=L.rectangle([anchor.latlng,anchor.latlng],{color:'#183d50',weight:2,dashArray:'6 4',fillOpacity:.08,interactive:false}).addTo(map);
  },true);
  element.addEventListener('pointermove',event=>{
    if(!drawing||!anchor||event.pointerId!==pointer)return;
    preview.setBounds(L.latLngBounds(anchor.latlng,map.mouseEventToLatLng(event)));
  });
  element.addEventListener('pointerup',event=>{
    if(!drawing||!anchor||event.pointerId!==pointer)return;
    const start=anchor,end=map.mouseEventToLatLng(event),point=map.mouseEventToContainerPoint(event);
    if(element.hasPointerCapture(pointer))element.releasePointerCapture(pointer);
    setDrawing(false);
    if(Math.abs(point.x-start.point.x)<6||Math.abs(point.y-start.point.y)<6){onRead('The rectangle is too small. Choose Draw rectangle and drag a larger area.');return;}
    onSelect(drawnBounds(start.latlng,end));
  });
  element.addEventListener('pointercancel',()=>setDrawing(false));
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&drawing){setDrawing(false);onRead('Area drawing cancelled. Drag to pan the map.');}});
  map.on('mousemove click',e=>{
    const lon=((e.latlng.lng+180)%360+360)%360-180,lat=e.latlng.lat;
    const c=lookup.get(`${Math.floor((lat+90)/.25)},${Math.floor((lon+180)/.25)}`);
    const inside=!bounds||longitudeParts(bounds).some(([w,s,e,n])=>lon>=w&&lon<e&&lat>=s&&lat<n);
    if(!drawing)onRead(c&&inside ? `${currentMonth} · ${lat.toFixed(2)}° latitude, ${lon.toFixed(2)}° longitude · ${Math.round(c.value).toLocaleString('en-US')} VIIRS-equivalent detections in the full 0.25° cell · ${sourceLabel[c.source]??c.source}` : 'No supplied grid cell at this location within the selected area.');
  });
  function fit(active=true){
    if(bounds){const [w,s,e,n]=bounds;map.fitBounds([[Math.max(-85,s),w],[Math.min(85,n),e<w?e+360:e]],{padding:[30,30],maxZoom:11,animate:false});return;}
    const extent=active?activityExtent(cells):gridExtent(cells);
    if(extent)map.fitBounds(extent,{padding:[35,35],maxZoom:10,animate:false});
  }
  return {
    update(data,month,palette,area,key){
      currentMonth=month;color=palette;bounds=area;cells=[];lookup=new Map();max=1;
      const t=data?.months.indexOf(month)??-1;
      if(t>=0)for(let i=0;i<data.cells.lat_idx.length;i++){
        const value=data.est[i][t];if(value==null||!Number.isFinite(value))continue;
        const c={lat:data.cells.lat_idx[i]*.25-90,lon:data.cells.lon_idx[i]*.25-180,value,source:data.cell_sources?.[i]?.[t]??data.month_source[t]};
        cells.push(c);lookup.set(`${data.cells.lat_idx[i]},${data.cells.lon_idx[i]}`,c);
        if(!area||cellInBounds(c.lat,c.lon,area))max=Math.max(max,value);
      }
      selection.clearLayers();
      if(area){const [w,s,e,n]=area;L.rectangle([[s,w],[n,e<w?e+360:e]],{color:'#183d50',weight:2,fill:false,interactive:false}).addTo(selection);}
      const next=key+JSON.stringify(area);
      if(next!==lastKey){fit();lastKey=next;}
      layer.draw();return {max,cells:cells.length};
    },
    zoomIn:()=>map.zoomIn(),zoomOut:()=>map.zoomOut(),fit,setDrawing,
  };
}
