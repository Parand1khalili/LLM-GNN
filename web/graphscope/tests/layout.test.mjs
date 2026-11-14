import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {structuralLayout,egoIds} from '../src/graph-layout.ts';
import {validateLayout} from '../src/layout-data.ts';
import {LAYOUT_SHA256} from '../src/layout-pin.ts';
const bytes=readFileSync(new URL('../public/data/layout.v1.json',import.meta.url));
const topology=JSON.parse(readFileSync(new URL('../public/data/full-topology.json',import.meta.url)));
test('pinned structural layout covers every authentic ID and is reproducible',()=>{
 assert.equal(createHash('sha256').update(bytes).digest('hex'),LAYOUT_SHA256);const l=validateLayout(JSON.parse(bytes));
 const again=structuralLayout(topology.nodes,topology.edges);assert.deepEqual(l.positions,again.positions);assert.equal(again.componentCount,78);
});
test('ego views contain genuine one/two hop neighbors and induced edges only',()=>{
 const edges=topology.edges.map(([source,target])=>({source,target}));const one=egoIds(edges,2628,1),two=egoIds(edges,2628,2);
 assert.equal(one.length,45);assert.ok(two.length>one.length);assert.ok(one.every(n=>two.includes(n)));
 assert.deepEqual(one.filter(n=>n!==2628),edges.flatMap(e=>e.source===2628?[e.target]:e.target===2628?[e.source]:[]).sort((a,b)=>a-b));
});
test('reject changed layout identity, coordinates, missing nodes and unknown fields',()=>{
 for(const mutate of [x=>x.gt=[],x=>x.positions.pop(),x=>x.positions[0][0]=1,x=>x.positions[0][1]=Infinity,x=>x.topologySHA='a'.repeat(64)]){const x=JSON.parse(bytes);mutate(x);assert.throws(()=>validateLayout(x));}
});

test('ego hop input is bounded before graph traversal',()=>{for(const h of [Infinity,1e9,-1,1.2,NaN])assert.throws(()=>egoIds([],0,h));});
