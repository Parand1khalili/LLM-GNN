import {check,exact,checkedJSON} from './benchmark.ts';
import {TOPOLOGY_SHA256} from './topology-pin.ts';
import {LAYOUT_SHA256} from './layout-pin.ts';
export type GraphLayout={schema:string;topologySHA:string;algorithm:string;componentCount:number;positions:number[][]};
export function validateLayout(input:unknown):GraphLayout {exact(input,['schema','topologySHA','algorithm','componentCount','positions']);const l=input as unknown as GraphLayout;check(l.schema==='graphscope.layout.v1'&&l.topologySHA===TOPOLOGY_SHA256&&l.algorithm==='bounded-structural-partition-spring-v1'&&l.componentCount===78,'layout identity');check(Array.isArray(l.positions)&&l.positions.length===2708&&l.positions.every((p,i)=>Array.isArray(p)&&p.length===3&&p[0]===i&&p.slice(1).every(n=>typeof n==='number'&&Number.isFinite(n)&&Math.abs(n)<100000)),'layout coordinates');return l;}
let cached:Promise<GraphLayout>|undefined;
export function loadLayout(){return cached??=fetch(`${import.meta.env.BASE_URL}data/layout.v1.json`).then(async r=>{if(!r.ok)throw Error(`Layout HTTP ${r.status}`);return validateLayout(await checkedJSON(await r.arrayBuffer(),LAYOUT_SHA256));});}
