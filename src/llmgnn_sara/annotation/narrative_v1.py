"""GT-free paired Narrative v1 preparation, no provider or training entry point."""
import hashlib,json,pickletools,struct,zipfile
from pathlib import Path
from itertools import combinations
from .prompts import FrozenPromptTemplate,build_narrative_prompt
from ..io.project import load_project_inputs,GRAPH_SHA256,PINS
from ..io.frozen import read_pinned_json
from ..io.frozen import reject_gt
from ..pilot.workflow import _local_counter
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest

SPEC={"schema":"sara.narrative.v1.paired_spec.v1","arms":["v1-A","v1-B"],"K":4,
 "neighbor_tokens":128,"prompt_ceiling":4096,"tokenizer":"cl100k_base",
 "selection":"frozen neighbor order first, then ascending remaining direct IDs; up to K nonblank original texts",
 "target":"full original text, never truncate","output":"historical wrapper top3 answer/confidence JSON list; sum100",
 "historical_model":{"model":"gpt-6-luna","temperature":0.7,"n":1,"samples_per_arm":3,"max_tokens":"OMITTED_HISTORICALLY"},
 "execution":"NOT_AUTHORIZED; require contemporaneous verified model/version and approved decoding/privacy/budget",
 "evaluation":{"primary":"paired v1-B minus v1-A all140 top1 accuracy",
 "secondary":["classwise PRF","confusion","corrections/regressions","degree","evidence availability",
 "posthoc homophily","joint baseline errors","cost","sample variability"],
 "GT":"separate future evaluator only after prediction freeze"}}
INSTRUCTIONS={
 "v1-A":"Classify the target paper's primary research topic. Neighbor texts are auxiliary evidence. Prioritize the target paper.",
 "v1-B":"Identify the target paper's primary research problem and contribution, separating auxiliary methods and background. Independently assess each neighbor as supporting, contradictory, ambiguous or irrelevant. Connections do not imply equal classes. Synthesize evidence while prioritizing target text; neighborhood consensus is not proof. Return only the required final predictions, without reasoning traces."}

def sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()

def extract_sources(path):
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError("Unsafe graph")
    blob=path.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=GRAPH_SHA256:raise ValueError("Graph hash")
    with zipfile.ZipFile(path) as archive:
        ops=list(pickletools.genops(archive.read('cora_random_sbert/data.pkl')))
        start=next(i for i,x in enumerate(ops) if x[1]=='raw_text')
        texts=[];memo={};last=None
        for op,arg,_ in ops[start+4:]:
            if op.name=='BINUNICODE':last=arg;texts.append(arg)
            elif op.name in ('BINPUT','LONG_BINPUT'):memo[arg]=last
            elif op.name in ('BINGET','LONG_BINGET'):last=memo[arg];texts.append(last)
            elif op.name not in ('MARK','APPENDS'):raise ValueError("Unexpected text-list opcode")
            if len(texts)==2708:break
        if len(texts)!=2708 or any(type(t)is not str for t in texts):raise ValueError("Text mapping")
        raw=archive.read('cora_random_sbert/data/1')
    values=struct.unpack('<21716q',raw);adj=[set() for _ in texts]
    for a,b in zip(values[:10858],values[10858:]):
        if not 0<=a<2708 or not 0<=b<2708 or a==b:raise ValueError("Edge domain")
        adj[a].add(b)
    if not all(i in adj[j] for i,ns in enumerate(adj) for j in ns):raise ValueError("Asymmetric graph")
    return texts,adj

def prefix(text,budget,count):
    lo,hi=0,len(text)
    while lo<hi:
        mid=(lo+hi+1)//2
        if count(text[:mid])<=budget:lo=mid
        else:hi=mid-1
    # Character prefixes remain verbatim even across UTF8 token boundaries.
    return text[:lo]

def evidence(node,target,historical,texts,adj,count):
    if len(texts)!=len(adj) or any(type(t)is not str for t in texts):raise ValueError('Text/graph alignment')
    if any(type(j)is not int or not 0<=j<len(adj) or j==i or i not in adj[j]
           for i,neighbors in enumerate(adj) for j in neighbors):raise ValueError('Undirected adjacency required')
    if type(node)is not int or not 0<=node<len(texts) or texts[node]!=target:raise ValueError("Target identity")
    if len(set(historical))!=len(historical) or not set(historical)<=adj[node]:raise ValueError("Historical neighbors")
    order=list(historical)+sorted(adj[node]-set(historical))
    selected=[i for i in order if texts[i].strip()][:SPEC['K']]
    snippets=[]
    for i in selected:
        short=prefix(texts[i],SPEC['neighbor_tokens'],count)
        if not short or short not in texts[i]:raise ValueError("Missing authentic neighbor text")
        snippets.append(dict(source_id=f'neighbor:{i}',node_id=i,text=short,source_sha256=sha(texts[i]),
            snippet_sha256=sha(short),source_tokens=count(texts[i]),snippet_tokens=count(short),truncated=short!=texts[i]))
    return dict(target=dict(node_id=node,text=target,sha256=sha(target)),neighbors=snippets,
        graph=dict(direct_degree=len(adj[node]),all_neighbors_are_direct=True,
            connected_pairs=[list(p) for p in combinations(selected,2) if p[1] in adj[p[0]]]))

def prompts(bundle,template,count):
    reject_gt(bundle)
    target=bundle['target'];neighbors=bundle['neighbors']
    if sha(target['text'])!=target['sha256']:raise ValueError('Target hash')
    if len(neighbors)>SPEC['K'] or len({n['node_id'] for n in neighbors})!=len(neighbors):raise ValueError('Neighbor count/identity')
    for neighbor in neighbors:
        if (not neighbor['text'] or sha(neighbor['text'])!=neighbor['snippet_sha256']
                or neighbor['snippet_tokens']!=count(neighbor['text'])
                or count(neighbor['text'])>SPEC['neighbor_tokens']):raise ValueError('Snippet hash/token count')
    body=json.dumps(bundle,ensure_ascii=False,sort_keys=True)
    result={arm:template.wrap(body+'\n\n'+instruction) for arm,instruction in INSTRUCTIONS.items()}
    if any(count(p)>SPEC['prompt_ceiling'] for p in result.values()):raise ValueError("Prompt cap; target never displaced")
    return result

def main():
    store=PrivateAudit('.local_artifacts/narrative_v1')
    spec={**SPEC,"instructions":INSTRUCTIONS,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "historical_fingerprints":PINS}
    spec_sha=store.write(spec) # Before constructing any experimental prompt.
    inputs=load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic')
    texts,adj=extract_sources('.local_artifacts/gt_reference/cora_random_sbert.pt')
    template=FrozenPromptTemplate.from_receipt('.local_artifacts/frozen/preparation_receipt.json')
    framed=_local_counter('.local_artifacts/tokenizer_cache');count=lambda text:framed(text)-64
    historical=read_pinned_json('.local_artifacts/authentic/narrative_prompts.json',PINS['narrative_prompts.json'])
    rows=[]
    for pair in inputs.pairs:
        n=pair.neighborhood
        if any(b not in adj[a] for a,b in n.connected_pairs) or any(b in adj[a] for a,b in n.disconnected_pairs):
            raise ValueError('Historical topology differs from pinned graph')
        bundle=evidence(pair.node_id,pair.text,n.neighbor_ids,texts,adj,count)
        built=prompts(bundle,template,count)
        if len(adj[pair.node_id])!=n.degree:raise ValueError("Frozen degree differs")
        row=dict(node_id=pair.node_id,evidence=bundle,evidence_sha256=digest(bundle),
            prompts=built,prompt_sha256={k:sha(v) for k,v in built.items()},tokens={k:count(v) for k,v in built.items()},
            historical=dict(prompt_sha256=sha(historical['prompts_by_target_id'][str(pair.node_id)]),
                tokens=count(historical['prompts_by_target_id'][str(pair.node_id)]),selected=len(n.neighbor_ids),
                independent_texts=1 if n.representative_id is not None else 0,
                representative_id=n.representative_id,representative_dominates_explicit_abstract=True,
                connected_pairs=len(n.connected_pairs),disconnected_pairs=len(n.disconnected_pairs),
                accessible_selected_texts=sum(bool(texts[i].strip()) for i in n.neighbor_ids)),
            request_skeleton={a:dict(prompt_sha256=sha(p),status='NOT_RUN_NOT_PREDICTIONS') for a,p in built.items()})
        row['historical']['selected_neighbor_text_lengths']=[len(texts[i]) for i in n.neighbor_ids]
        row['historical']['representative_original_text_length']=len(texts[n.representative_id]) if n.representative_id is not None else None
        row['historical']['representative_full_text_present']=texts[n.representative_id] in historical['prompts_by_target_id'][str(pair.node_id)] if n.representative_id is not None else None
        row['historical']['context_tokens']=count(n.context)
        rows.append(row)
    result=dict(schema='sara.narrative.v1.prompt_freeze.v1',spec_sha256=spec_sha,source_fingerprints=dict(inputs.provenance),
        graph_sha256=GRAPH_SHA256,texts_sha256=digest(texts),rows=rows,status='GT_FREE_PROMPTS_ONLY_NOT_LLM_OUTPUT')
    freeze_sha=store.write(result);assert store.read(freeze_sha)==result
    import statistics
    aggregate=dict(spec_sha256=spec_sha,freeze_sha256=freeze_sha,targets=len(rows),
        independent_neighbor_texts=dict(Counter(len(r['evidence']['neighbors']) for r in rows)),
        truncated_neighbors=sum(n['truncated'] for r in rows for n in r['evidence']['neighbors']),
        token_stats={k:dict(min=min(r['tokens'][k] for r in rows),max=max(r['tokens'][k] for r in rows),
            mean=statistics.mean(r['tokens'][k] for r in rows)) for k in INSTRUCTIONS},
        historical_tokens=dict(min=min(r['historical']['tokens'] for r in rows),max=max(r['historical']['tokens'] for r in rows)),
        historical_selected_distribution=dict(Counter(r['historical']['selected'] for r in rows)),
        historical_connected_pairs=sum(r['historical']['connected_pairs'] for r in rows),
        historical_disconnected_pairs=sum(r['historical']['disconnected_pairs'] for r in rows),
        degree=dict(min=min(r['evidence']['graph']['direct_degree'] for r in rows),max=max(r['evidence']['graph']['direct_degree'] for r in rows)),
        no_gt=True,api_calls=0,training_runs=0,readiness='NOT_AUTHORIZED_FOR_PAID_EXECUTION')
    Path('reports/narrative_v1_prompt_audit.json').write_text(json.dumps(aggregate,indent=2)+'\n',encoding='utf8')
    print(json.dumps(aggregate))
from collections import Counter
if __name__=='__main__':main()
