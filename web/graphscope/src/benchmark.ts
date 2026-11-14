export const ARM_IDS = ['current_B1','current_v0','current_v1-A','current_v1-B','current_v1-C','current_v1-D','historical_A_B1','historical_B_NARRATIVE','historical_C_BASELINE_FUSION','historical_Expanded_V1','historical_V1_r0','historical_V1_r1_v1','lite','lite_class_count_control','lite_exact_mask_control','lite_router_only'] as const;
export type FinalArm = { id:string;cohort:string;loss:string;postFilter:boolean;mask:string;trainCount:number;testCount:number;coverage:number;accuracy:number;sd:number;macroF1:number;macroF1SD:number;raw:{correct:number;wrong:number;abstained:number;unavailable:number};seeds:{seed:number;accuracy:number;macroF1:number}[];fitSHA:string;vectorSHA:string;maskSHA:string;sourceSHA:string;aliasOf:string|null };
export type Benchmark = {schema:string;snapshotDate:string;graphSHA:string;manifestSHA:string;gtResultSHA:string;testSHA:string;classOrder:string[];status:string;newFits:number;reusedFits:number;uniqueSpecs:number;arms:FinalArm[];sources:{path:string;sha256:string;repositorySHA256:string}[];ownerSHA:string;liteActions:{KEEP:number;SWITCH:number;ABSTAIN:number;UNAVAILABLE:number};historicalWCE:{id:string;loss:string;cohort:string;accuracy:number;sd:number;trainCount:number;fitSHA:string;source:string}};
export type OwnerEvidence = {schema:string;manifestSHA:string;classOrder:string[];targetIds:number[];arms:{id:string;maskSHA:string;vectorSHA:string;labels:(number|null)[];confidence:(number|null)[]}[]};
export function check(ok:unknown,msg:string):asserts ok {if(!ok)throw new Error(`Research data rejected: ${msg}`);}
export function exact(v:unknown,keys:string[]):asserts v is Record<string,unknown> {check(!!v&&typeof v==='object'&&!Array.isArray(v),'object');check(Object.keys(v).length===keys.length&&Object.keys(v).every(k=>keys.includes(k)),'unknown or missing fields');}
const finite=(n:unknown,lo=0,hi=100):n is number=>typeof n==='number'&&Number.isFinite(n)&&n>=lo&&n<=hi;
const hash=(s:unknown)=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
export const mean=(xs:number[])=>xs.reduce((a,b)=>a+b,0)/xs.length;
export const sd=(xs:number[])=>Math.sqrt(mean(xs.map(x=>(x-mean(xs))**2)));
export function validateBenchmark(input:unknown):Benchmark {
 exact(input,'schema snapshotDate graphSHA manifestSHA gtResultSHA testSHA classOrder status newFits reusedFits uniqueSpecs arms sources ownerSHA liteActions historicalWCE'.split(' '));
 const b=input as unknown as Benchmark;
 check(b.schema==='graphscope.benchmark.v3'&&b.snapshotDate==='2026-11-13','schema/date');
 check(b.manifestSHA==='d3eaca9ce2e87f98d73af6d7664a80ac377b297fe252ba7911b6ee24693eca7e'&&b.gtResultSHA==='bf2f25c1fadc231f8921bd06caf324b52aecccb424d26cb569feaab27e42ee7b','freeze');
 check([b.graphSHA,b.testSHA,b.ownerSHA].every(hash)&&b.newFits===110&&b.reusedFits===40&&b.uniqueSpecs===15,'hash/fit accounting');
 check(JSON.stringify(b.classOrder)===JSON.stringify(['rule_learning','neural_networks','case_based','genetic_algorithms','theory','reinforcement_learning','probabilistic_methods']),'class order');
 check(b.status==='LIMITED_PROVENANCE_EXPLORATORY / EXPLORATORY_NOT_INDEPENDENT','evidence status');
 check(Array.isArray(b.arms)&&b.arms.length===16&&b.arms.every((a,i)=>a.id===ARM_IDS[i]),'arm identity');
 for(const a of b.arms){
  exact(a,'id cohort loss postFilter mask trainCount testCount coverage accuracy sd macroF1 macroF1SD raw seeds fitSHA vectorSHA maskSHA sourceSHA aliasOf'.split(' '));
  check(a.cohort==='Sensitivity140'&&a.loss==='CE'&&a.postFilter===false&&a.mask==='Natural'&&a.testCount===2568,'comparison contract');
  check(Number.isInteger(a.trainCount)&&finite(a.trainCount,1,140)&&a.coverage===a.trainCount/140,'mask/coverage');
  check([a.fitSHA,a.vectorSHA,a.maskSHA,a.sourceSHA].every(hash),'arm hashes');
  check(finite(a.accuracy)&&finite(a.sd)&&finite(a.macroF1,0,1)&&finite(a.macroF1SD,0,1),'metrics');
  exact(a.raw,['correct','wrong','abstained','unavailable']);check(Object.values(a.raw).every(n=>Number.isInteger(n)&&finite(n,0,140))&&Object.values(a.raw).reduce((x,y)=>x+y,0)===140&&a.raw.correct+a.raw.wrong===a.trainCount,'raw counts');
  check(Array.isArray(a.seeds)&&a.seeds.length===10,'seed count');
  a.seeds.forEach((s,i)=>{exact(s,['seed','accuracy','macroF1']);check(s.seed===i&&finite(s.accuracy)&&finite(s.macroF1,0,1),'seed identity/values');});
  for(const [key,m,d] of [['accuracy',a.accuracy,a.sd],['macroF1',a.macroF1,a.macroF1SD]] as const){const ns=a.seeds.map(s=>s[key]);check(Math.abs(mean(ns)-m)<1e-9&&Math.abs(sd(ns)-d)<1e-9,'seed-derived statistics');}
  check(a.aliasOf===(a.id==='historical_V1_r0'?'historical_C_BASELINE_FUSION':null),'alias identity');
 }
 check(new Set(b.arms.map(a=>a.fitSHA)).size===15,'unique specs');
 const alias=b.arms.find(a=>a.aliasOf)!;const base=b.arms.find(a=>a.id===alias.aliasOf)!;check(['fitSHA','vectorSHA','maskSHA','accuracy','sd'].every(k=>aField(alias,k)===aField(base,k)),'alias mismatch');
 check(Array.isArray(b.sources)&&b.sources.length===8,'sources');for(const s of b.sources){exact(s,['path','sha256','repositorySHA256']);check(/^reports\/[a-z0-9_]+\.(csv|json)$/.test(s.path)&&hash(s.sha256)&&hash(s.repositorySHA256),'source provenance');}
 check(new Set(b.sources.map(s=>s.path)).size===8,'source duplicates');exact(b.liteActions,['KEEP','SWITCH','ABSTAIN','UNAVAILABLE']);check(b.liteActions.KEEP===22&&b.liteActions.SWITCH===4&&b.liteActions.ABSTAIN===1&&b.liteActions.UNAVAILABLE===10,'lite actions');exact(b.historicalWCE,['id','loss','cohort','accuracy','sd','trainCount','fitSHA','source']);check(b.historicalWCE.id==='historical_V1_r1_v1_WCE'&&b.historicalWCE.loss==='WCE'&&b.historicalWCE.cohort==='Sensitivity140'&&b.historicalWCE.trainCount===78&&finite(b.historicalWCE.accuracy)&&finite(b.historicalWCE.sd)&&hash(b.historicalWCE.fitSHA)&&b.historicalWCE.source==='reports/gcn_missing_experiments_results.csv','historical WCE');return b;
}
function aField(a:FinalArm,k:string){return a[k as keyof FinalArm];}
export function paired(a:FinalArm,b:FinalArm){check(a.cohort===b.cohort&&a.loss===b.loss&&a.postFilter===b.postFilter&&a.testCount===b.testCount&&a.seeds.every((s,i)=>s.seed===b.seeds[i]?.seed),'incompatible paired comparison');const ds=a.seeds.map((s,i)=>s.accuracy-b.seeds[i].accuracy);return {mean:mean(ds),sd:sd(ds),positive:ds.filter(x=>x>1e-10).length,negative:ds.filter(x=>x< -1e-10).length,ties:ds.filter(x=>Math.abs(x)<=1e-10).length};}
export async function sha256(bytes:BufferSource){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export async function checkedJSON(bytes:ArrayBuffer,expected:string){check(bytes.byteLength<1500000,'file size');check(await sha256(bytes)===expected,'checksum conflict');return JSON.parse(new TextDecoder().decode(bytes)) as unknown;}
export function validateOwner(input:unknown,b:Benchmark):OwnerEvidence {
 exact(input,['schema','manifestSHA','classOrder','targetIds','arms']);const o=input as unknown as OwnerEvidence;
 check(o.schema==='graphscope.owner.v1'&&o.manifestSHA===b.manifestSHA&&JSON.stringify(o.classOrder)===JSON.stringify(b.classOrder),'owner identity');
 check(Array.isArray(o.targetIds)&&o.targetIds.length===140&&o.targetIds.every((n,i)=>Number.isInteger(n)&&n>=0&&n<2708&&(i===0||n>o.targetIds[i-1])),'owner IDs');
 check(Array.isArray(o.arms)&&o.arms.length===16,'owner arms');o.arms.forEach((a,i)=>{exact(a,['id','maskSHA','vectorSHA','labels','confidence']);const pub=b.arms[i];check(a.id===pub.id&&a.maskSHA===pub.maskSHA&&a.vectorSHA===pub.vectorSHA,'owner hashes');check(Array.isArray(a.labels)&&a.labels.length===140&&a.labels.every(c=>c===null||Number.isInteger(c)&&c>=0&&c<7)&&a.labels.filter(c=>c!==null).length===pub.trainCount,'owner labels/mask');check(Array.isArray(a.confidence)&&a.confidence.length===140&&a.confidence.every(c=>c===null||finite(c)), 'owner confidence');});
 const v=o.arms.find(a=>a.id==='current_v0')!,r=o.arms.find(a=>a.id==='lite_router_only')!;check(r.labels.every((c,i)=>c===null||c===v.labels[i]),'router changed class');return o;
}
export const armName=(id:string)=>({'current_B1':'B1 · current','current_v0':'Narrative v0 · current','lite_router_only':'SARA-Core · Router-only','lite':'SARA-Lite','lite_exact_mask_control':'Exact-mask control','lite_class_count_control':'Class-count control','historical_V1_r0':'Historical V1/R0 · Fusion alias','historical_V1_r1_v1':'Historical V1/R1 CE'}[id]??id.replaceAll('_',' '));
export function download(name:string,content:string,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
