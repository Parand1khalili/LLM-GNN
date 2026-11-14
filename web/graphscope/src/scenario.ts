import type {Benchmark,OwnerEvidence} from './benchmark.ts';
import {check} from './benchmark.ts';
export function scenarioPlan(b:Benchmark,owner:OwnerEvidence|null,armId:string,seed:number,excluded:number[]){
 const arm=b.arms.find(a=>a.id===armId);check(arm,'unknown scenario arm');check(Number.isInteger(seed)&&seed>=0&&seed<=9,'scenario seed');
 check(new Set(excluded).size===excluded.length&&excluded.every(n=>Number.isInteger(n)&&n>=0&&n<2708),'scenario IDs');
 const vector=owner?.arms.find(a=>a.id===armId);
 const base=owner&&vector?owner.targetIds.filter((_,i)=>vector.labels[i]!==null):null;
 check(base!==null||excluded.length===0,'private mask unavailable');check(excluded.every(n=>base!.includes(n)),'excluded ID not in frozen mask');
 const retained=base?.filter(n=>!excluded.includes(n))??null;
 return {schema:'graphscope.scenario.v1',status:'UNEXECUTED_WHAT_IF',dataset:'Cora-2708',cohort:'Sensitivity140',manifestSHA:b.manifestSHA,graphSHA:b.graphSHA,testSHA:b.testSHA,sourceArm:armId,sourceVectorSHA:arm.vectorSHA,sourceMaskSHA:arm.maskSHA,sourceFitSHA:arm.fitSHA,seed,mode:'mask-inspection-only',excludedIds:[...excluded].sort((a,c)=>a-c),retainedIds:retained,retainedCount:retained?.length??null,maskAvailability:retained?'OWNER_LOCAL_IMPORTED':'UNAVAILABLE',router:armId==='lite_router_only'?'sara.router.r1_candidate.v1':null,frozenRouterBudget:armId==='lite_router_only'?37:null,parameters:{layers:2,hidden:64,dropout:0.5,epochs:30,learningRate:0.01,weightDecay:0.0005,loss:'CE',postFilter:false,checkpoint:'last-epoch'},execution:'NOT_AUTHORIZED_NO_RUNNER',newResultAvailable:false};
}
