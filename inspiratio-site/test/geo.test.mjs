import test from 'node:test';
import assert from 'node:assert/strict';
import { gridExtent, activityExtent, cellInBounds } from '../src/lib/v2/geo.js';
import { boxWeight, subset } from '../src/lib/v2/science.js';

test('date-line cells stay adjacent and ordinary California bounds stay local',()=>{
  assert.deepEqual(gridExtent([{lat:0,lon:179.75},{lat:0,lon:-180}]),[[0,179.75],[.25,180.25]]);
  assert.deepEqual(gridExtent([{lat:32,lon:-124},{lat:42,lon:-114}]),[[32,-124],[42.25,-113.75]]);
});
test('full-world and crossing bounds include both sides without double-counting',()=>{
  for(const lon of [-180,179.75]) {
    assert.equal(boxWeight(0,lon,[-180,-90,180,90]),1);
    assert.equal(boxWeight(0,lon,[170,-1,-170,1]),1);
    assert.equal(cellInBounds(0,lon,[170,-1,-170,1]),true);
  }
  assert.equal(boxWeight(0,0,[170,-1,-170,1]),0);
  assert.equal(boxWeight(0,179.75,[179.875,0,-179.875,.25]),.5);
});
test('main activity camera excludes distant low-count cells without mutating data',()=>{
  const cells=[{lat:-78,lon:90,value:1},{lat:-35,lon:120,value:500},{lat:-15,lon:140,value:500}];
  assert.deepEqual(activityExtent(cells),[[-35,120],[-14.75,140.25]]);
  assert.equal(cells.length,3);
  assert.deepEqual(activityExtent([{lat:0,lon:179.75,value:100},{lat:0,lon:-180,value:100}]),[[0,179.75],[.25,180.25]]);
});
test('custom date-line area totals use both sides and preserve missing values',()=>{
  const d={months:['2020-01'],totals:{est:[60]},month_source:['model_aqua'],month_nrt:[false],month_input_complete:[true],cells:{lat_idx:[360,360,360],lon_idx:[1439,0,720]},est:[[10],[20],[30]]};
  assert.equal(subset(d,[170,-1,-170,1])[0].value,30);
  assert.equal(subset(d,[-180,-90,180,90])[0].value,60);
  d.est[0][0]=null;
  assert.equal(subset(d,[170,-1,-170,1])[0].value,null);
  for(const b of [[181,0,10,1],[-10,0,-181,1],[0,0,0,1]])assert.throws(()=>subset(d,b));
});
