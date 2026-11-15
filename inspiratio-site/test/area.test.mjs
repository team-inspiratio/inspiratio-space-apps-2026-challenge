import test from 'node:test';
import assert from 'node:assert/strict';
import { areaCandidates, createAreaCollector } from '../src/lib/v2/area.js';
import { drawnBounds } from '../src/lib/v2/geo.js';
const region=(name,lon,source='snpp')=>({name,label:name,role:'train',rawData:{months:['2022-08'],cells:{lat_idx:[360],lon_idx:[lon]},est:[[10]],totals:{est:[10]},month_source:[source],month_nrt:[false],month_input_complete:[true]}});
test('area loading spans partitions and excludes overlapping demonstration boxes',()=>{
  const items=[{name:'a',kind:'region',bbox:[0,0,.25,.25]},{name:'b',kind:'region',bbox:[.25,0,.5,.25]},{name:'demo',kind:'box',bbox:[0,0,.5,.25]}];
  assert.deepEqual(areaCandidates(items,[0,0,.5,.25]).map(x=>x.name),['a','b']);
  const c=createAreaCollector([0,0,.375,.25]);c.add(region('a',720));c.add(region('b',721,'model_aqua'));
  const result=c.finish();assert.equal(result.series[0].value,15);assert.equal(result.series[0].source,'mixed');
  assert.equal(result.series[0].lo,null);assert.equal(result.cellCount,2);assert.equal(result.regions.length,2);
});
test('duplicate cells are errors and missing selected data remain missing',()=>{
  const c=createAreaCollector([0,0,.25,.25]);c.add(region('a',720));assert.throws(()=>c.add(region('duplicate',720)));
  const missing=region('missing',720);missing.rawData.est[0][0]=null;
  const m=createAreaCollector([0,0,.25,.25]);m.add(missing);assert.equal(m.finish().series[0].value,null);
  assert.throws(()=>createAreaCollector([0,0,.25,.25]).finish());
});
test('drawn rectangles handle either drag direction and cross the date line',()=>{
  assert.deepEqual(drawnBounds({lat:30,lng:106},{lat:29,lng:108}),[106,29,108,30]);
  assert.deepEqual(drawnBounds({lat:29,lng:108},{lat:30,lng:106}),[106,29,108,30]);
  assert.deepEqual(drawnBounds({lat:10,lng:170},{lat:-10,lng:190}),[170,-10,-170,10]);
});
