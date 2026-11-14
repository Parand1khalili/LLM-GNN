/** Display-only deterministic structural partition and bounded spring layout.
 * Never uses classes, annotation confidence or ground truth. */
export function structuralLayout(ids:number[],edges:[number,number][]){
 const adjacency=new Map(ids.map(id=>[id,[] as number[]]));for(const [a,b] of edges){adjacency.get(a)!.push(b);adjacency.get(b)!.push(a);}for(const ns of adjacency.values())ns.sort((a,b)=>a-b);
 const remaining=new Set(ids),components:number[][]=[];
 while(remaining.size){const root=Math.min(...remaining),q=[root];remaining.delete(root);for(let i=0;i<q.length;i++)for(const n of adjacency.get(q[i])!)if(remaining.delete(n))q.push(n);components.push(q);}
 components.sort((a,b)=>b.length-a.length||Math.min(...a)-Math.min(...b));
 const positions=new Map<number,{x:number;y:number}>();let shelfX=0,shelfY=0,shelfH=0;
 for(const component of components){
  const unassigned=new Set(component),clusters:number[][]=[],membership=new Map<number,number>();
  const priority=[...component].sort((a,b)=>adjacency.get(b)!.length-adjacency.get(a)!.length||a-b);
  while(unassigned.size){const root=priority.find(n=>unassigned.has(n))!,queue=[root],group:number[]=[];const queued=new Set(queue);
   for(let i=0;i<queue.length&&group.length<32;i++){const n=queue[i];if(!unassigned.delete(n))continue;group.push(n);for(const next of adjacency.get(n)!)if(unassigned.has(next)&&!queued.has(next)){queue.push(next);queued.add(next);}}
   for(const n of group)membership.set(n,clusters.length);clusters.push(group);
  }
  const centers=clusters.map((_,i)=>({x:Math.cos(i*2.399963)*Math.sqrt(i)*140,y:Math.sin(i*2.399963)*Math.sqrt(i)*140}));
  const links=new Map<string,number>();for(const a of component)for(const b of adjacency.get(a)!){if(a>=b)continue;let u=membership.get(a)!,v=membership.get(b)!;if(u===v)continue;if(u>v)[u,v]=[v,u];const k=`${u}:${v}`;links.set(k,(links.get(k)??0)+1);}
  for(let iteration=0;iteration<140;iteration++){
   const force=centers.map(()=>({x:0,y:0}));
   for(let i=0;i<centers.length;i++)for(let j=i+1;j<centers.length;j++){let dx=centers[i].x-centers[j].x,dy=centers[i].y-centers[j].y;const d2=Math.max(64,dx*dx+dy*dy),k=16000/d2;force[i].x+=dx*k;force[i].y+=dy*k;force[j].x-=dx*k;force[j].y-=dy*k;}
   for(const [key,weight] of links){const [i,j]=key.split(':').map(Number);const dx=centers[j].x-centers[i].x,dy=centers[j].y-centers[i].y,d=Math.max(1,Math.hypot(dx,dy));const k=(d-190)/d*.025*Math.min(3,Math.sqrt(weight));force[i].x+=dx*k;force[i].y+=dy*k;force[j].x-=dx*k;force[j].y-=dy*k;}
   centers.forEach((c,i)=>{c.x+=Math.max(-12,Math.min(12,force[i].x));c.y+=Math.max(-12,Math.min(12,force[i].y));});
  }
  const local=new Map<number,{x:number;y:number}>();clusters.forEach((group,ci)=>{
   const ps=group.map((_,i)=>({x:Math.cos(i*2.399963)*Math.sqrt(i+1)*15,y:Math.sin(i*2.399963)*Math.sqrt(i+1)*15}));
   const index=new Map(group.map((n,i)=>[n,i]));
   for(let t=0;t<75;t++){
    const force=ps.map(()=>({x:0,y:0}));
    for(let i=0;i<ps.length;i++)for(let j=i+1;j<ps.length;j++){const dx=ps[i].x-ps[j].x,dy=ps[i].y-ps[j].y,k=360/Math.max(16,dx*dx+dy*dy);force[i].x+=dx*k;force[i].y+=dy*k;force[j].x-=dx*k;force[j].y-=dy*k;}
    group.forEach((n,i)=>{for(const m of adjacency.get(n)!){const j=index.get(m);if(j===undefined)continue;const dx=ps[j].x-ps[i].x,dy=ps[j].y-ps[i].y,d=Math.max(1,Math.hypot(dx,dy)),k=(d-28)/d*.035;force[i].x+=dx*k;force[i].y+=dy*k;}});
    ps.forEach((p,i)=>{p.x+=Math.max(-3,Math.min(3,force[i].x-p.x*.01));p.y+=Math.max(-3,Math.min(3,force[i].y-p.y*.01));});
   }
   group.forEach((n,i)=>local.set(n,{x:centers[ci].x+ps[i].x,y:centers[ci].y+ps[i].y}));
  });
  const values=[...local.values()],minX=Math.min(...values.map(p=>p.x)),minY=Math.min(...values.map(p=>p.y)),w=Math.max(...values.map(p=>p.x))-minX+120,h=Math.max(...values.map(p=>p.y))-minY+120;
  if(shelfX+w>3500&&shelfX>0){shelfY+=shelfH;shelfX=0;shelfH=0;}
  for(const [n,p] of local)positions.set(n,{x:Math.round((p.x-minX+shelfX+60)*100)/100,y:Math.round((p.y-minY+shelfY+60)*100)/100});
  shelfX+=w;shelfH=Math.max(shelfH,h);
 }
 return {positions:ids.map(id=>[id,positions.get(id)!.x,positions.get(id)!.y]),componentCount:components.length};
}
export function egoIds(edges:{source:number;target:number}[],selected:number,hops:number){if(!Number.isInteger(hops)||hops<0||hops>2)throw new Error('Ego hops must be 0, 1 or 2');const reached=new Set([selected]);let frontier=[selected];for(let i=0;i<hops&&frontier.length;i++){const next=new Set<number>();const f=new Set(frontier);for(const e of edges){if(f.has(e.source)&&!reached.has(e.target))next.add(e.target);if(f.has(e.target)&&!reached.has(e.source))next.add(e.source);}frontier=[...next];frontier.forEach(n=>reached.add(n));}return [...reached].sort((a,b)=>a-b);}
