import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {validateBenchmark,validateOwner,paired,checkedJSON} from '../src/benchmark.ts';
import {BENCHMARK_SHA256} from '../src/benchmark-pin.ts';
const bytes=readFileSync(new URL('../public/data/benchmark.v3.json',import.meta.url));
const raw=JSON.parse(bytes), b=validateBenchmark(raw);
const fresh=()=>structuredClone(raw);
const hash=x=>createHash('sha256').update(x).digest('hex');
const arm=id=>b.arms.find(a=>a.id===id);
test('final source bytes, 16 arms, 15 distinct specs and 150 effective fits',()=>{
 assert.equal(hash(bytes),BENCHMARK_SHA256);assert.equal(b.arms.length,16);assert.equal(new Set(b.arms.map(a=>a.fitSHA)).size,15);assert.equal(b.newFits+b.reusedFits,150);
 for(const s of b.sources){const bytes=readFileSync(new URL('../../../'+s.path,import.meta.url));assert.ok([s.sha256,s.repositorySHA256].includes(hash(bytes)));assert.equal(hash(Buffer.from(bytes.toString('utf8').replaceAll('\r\n','\n'))),s.repositorySHA256);}
});
test('independent CSV/seed joins reproduce every aggregate and diagnostic denominator',()=>{
 const csv=readFileSync(new URL('../../../reports/final_cora_gcn_results.csv',import.meta.url),'utf8').trim().split(/\r?\n/);const header=csv.shift().split(',');
 for(const line of csv){const r=Object.fromEntries(line.split(',').map((v,i)=>[header[i],v]));const a=arm(r.Arm);assert.equal(a.accuracy,Number(r.Accuracy));assert.equal(a.sd,Number(r.Accuracy_SD));assert.equal(a.macroF1,Number(r.Macro_F1));assert.equal(a.raw.correct+a.raw.wrong,a.trainCount);assert.equal(a.coverage,a.trainCount/140);}
});
test('selected Core and matched controls have actual paired differences',()=>{
 const core=arm('lite_router_only'),v0=arm('current_v0'),lite=arm('lite'),exact=arm('lite_exact_mask_control');
 assert.ok(Math.abs(core.accuracy-74.10046728971963)<1e-10);assert.ok(Math.abs(paired(core,v0).mean-1.66277258566978)<1e-9);
 assert.equal(paired(core,v0).positive,10);assert.equal(paired(lite,exact).positive,9);assert.equal(paired(lite,core).negative,10);assert.equal(lite.maskSHA,exact.maskSHA);
 assert.throws(()=>paired({...core,loss:'WCE'},v0),/incompatible/);
});
test('reject unknown fields, arm identity, missing seeds, wrong masks, invalid statistics and source fields',()=>{
 for(const mutate of [x=>x.gt=[],x=>x.arms[0].id='unknown',x=>x.arms[0].seeds.pop(),x=>x.arms[0].coverage=0,x=>x.arms[0].raw.correct++,x=>x.arms[0].loss='WCE',x=>x.arms[0].accuracy++,x=>x.arms[0].maskSHA='bad',x=>x.arms[0].seeds[0].seed=1,x=>x.sources[0].private=true,x=>x.arms[10].fitSHA='a'.repeat(64)]){const x=fresh();mutate(x);assert.throws(()=>validateBenchmark(x));}
});
test('checksum gate rejects altered JSON before schema interpretation',async()=>{
 const altered=Buffer.from(bytes);altered[30]^=1;await assert.rejects(checkedJSON(altered.buffer.slice(altered.byteOffset,altered.byteOffset+altered.byteLength),BENCHMARK_SHA256),/checksum/);
});
test('owner import never admits GT fields or an arbitrary payload',()=>{assert.throws(()=>validateOwner({schema:'graphscope.owner.v1',gt:[]},b));});
