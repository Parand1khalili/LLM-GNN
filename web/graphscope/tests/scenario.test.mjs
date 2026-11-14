import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {scenarioPlan} from '../src/scenario.ts';
import {validateBenchmark,validateOwner,checkedJSON} from '../src/benchmark.ts';
const b=validateBenchmark(JSON.parse(readFileSync(new URL('../public/data/benchmark.v3.json',import.meta.url))));
test('public scenario explicitly lacks private mask and never contains a new accuracy',()=>{
 const p=scenarioPlan(b,null,'lite_router_only',3,[]);assert.equal(p.status,'UNEXECUTED_WHAT_IF');assert.equal(p.retainedIds,null);assert.equal(p.maskAvailability,'UNAVAILABLE');assert.equal(p.newResultAvailable,false);assert.ok(!JSON.stringify(p).includes('accuracy'));assert.deepEqual(p,scenarioPlan(b,null,'lite_router_only',3,[]));
 assert.throws(()=>scenarioPlan(b,null,'lite_router_only',3,[25]),/mask unavailable/);
});
test('scenario rejects invented arms, seeds and out-of-mask IDs',()=>{for(const args of [['not-real',0,[]],['lite',12,[]],['lite',0,[-1]]])assert.throws(()=>scenarioPlan(b,null,...args));});
const file=new URL('../.qa/owner-evidence.json',import.meta.url);
test('local owner derivative verifies checksum, current mask and exact set difference',{skip:!existsSync(file)},async()=>{
 const bytes=readFileSync(file);const owner=validateOwner(await checkedJSON(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),b.ownerSHA),b);
 const plan=scenarioPlan(b,owner,'lite_router_only',0,[]);assert.equal(plan.retainedCount,103);
 const x=scenarioPlan(b,owner,'lite_router_only',0,[plan.retainedIds[0]]);assert.equal(x.retainedCount,102);assert.equal(plan.retainedCount,103);assert.equal(x.excludedIds.length,1);
 const bad=structuredClone(owner);bad.arms[0].gt=[];assert.throws(()=>validateOwner(bad,b));
 const invalid=owner.targetIds.find(n=>!plan.retainedIds.includes(n));assert.throws(()=>scenarioPlan(b,owner,'lite_router_only',0,[invalid]));
});

test('non-Core scenarios never claim the Core router produced their masks',()=>{const p=scenarioPlan(b,null,'current_B1',0,[]);assert.equal(p.router,null);assert.equal(p.frozenRouterBudget,null);});
