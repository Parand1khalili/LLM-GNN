// Synthetic topology exists only in this test; never exported to public data.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateTopology,topologyAtlas} from '../src/topology.ts';
import {createHash} from 'node:crypto';
import {TOPOLOGY_SHA256} from '../src/topology-pin.ts';
const atlas=JSON.parse(readFileSync(new URL('../public/data/atlas.v2.json',import.meta.url)));
function fixture(){
 const edges=new Map(atlas.edges.map(e=>[`${e.source}:${e.target}`,[e.source,e.target]]));
 for(let i=0;i<2707;i++) edges.set(`${i}:${i+1}`,[i,i+1]);
 return {schema:'graphscope.topology.v1',graphHash:atlas.graphHash,sourceHash:'a'.repeat(64),manifestHash:'b'.repeat(64),rawEdgeCount:edges.size,duplicatesRemoved:0,nodes:Array.from({length:2708},(_,i)=>i),edges:[...edges.values()]};
}
test('full-view adapter keeps research annotations and adds topology-only nodes',()=>{
 const full=topologyAtlas(validateTopology(fixture(),atlas),atlas);
 assert.equal(full.nodes.length,2708);assert.equal(full.nodes.find(n=>n.id===1013).annotations.b1.label,'rule_learning');
 assert.equal(full.nodes.find(n=>!atlas.nodes.some(r=>r.id===n.id)).annotations,undefined);
});
test('reject unknown/GT fields, wrong graph, remapped IDs and duplicated edges',()=>{
 for(const mutate of [t=>t.gt=[],t=>t.graphHash='0'.repeat(64),t=>t.nodes[0]=2708,t=>t.edges.push(t.edges[0])]){const t=fixture();mutate(t);assert.throws(()=>validateTopology(t,atlas));}
});
test('reject missing evidence edges, self-loops and bad duplicate accounting',()=>{
 for(const mutate of [t=>t.edges=t.edges.filter(e=>e.join(':')!==`${atlas.edges[0].source}:${atlas.edges[0].target}`),t=>t.edges[0]=[1,1],t=>t.duplicatesRemoved=-1]){const t=fixture();mutate(t);assert.throws(()=>validateTopology(t,atlas));}
});
test('admitted original Cora has exact coverage, digest and research degrees',()=>{
 const bytes=readFileSync(new URL('../public/data/full-topology.json',import.meta.url));
 assert.equal(createHash('sha256').update(bytes).digest('hex'),TOPOLOGY_SHA256);
 const full=validateTopology(JSON.parse(bytes),atlas);
 assert.equal(full.nodes.length,2708);assert.equal(full.edges.length,5278);
 assert.equal(full.rawEdgeCount,10858);assert.equal(full.duplicatesRemoved,5580);
 const degree=new Map();for(const [a,b] of full.edges){degree.set(a,(degree.get(a)??0)+1);degree.set(b,(degree.get(b)??0)+1);}
 for(const n of atlas.nodes.filter(n=>n.target))assert.equal(degree.get(n.id),n.recordedDegree);
 const actual=topologyAtlas(full,atlas);assert.equal(actual.nodes.filter(n=>n.annotations).length,140);
 assert.equal(actual.nodes.find(n=>n.id===0).annotations,undefined);
});
