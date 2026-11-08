"""Six-arm GT-free request skeleton and provisional cost preflight. No HTTP path."""
import json
from pathlib import Path
from decimal import Decimal
from .narrative_v1 import sha
from .prompts import FrozenPromptTemplate
from ..io.project import PINS
from ..io.frozen import read_pinned_json,reject_gt
from ..pilot.workflow import _local_counter
from ..sara3.audit import PrivateAudit
from ..sara3.experiment import digest
PIN='916ef67f164202861dfb16e7144ad99d28f82c84a71e9b4d3a110fa3d0a40900'
EXTRA={
 'v1-C': 'Identify the dominant semantic theme across the independent neighbor texts. Distinguish substantive agreement from superficial keyword overlap. Compare this theme against the target paper and prioritize direct target evidence over any neighbor majority. Return only the required predictions without reasoning traces.',
 'v1-D': 'Compare evidence supporting the target probable class with evidence contradicting competing classes. Distinguish the primary research contribution from auxiliary methods. Consider uncertainty when target and neighborhood evidence conflict. Prioritize target evidence. Return only the required predictions without reasoning traces.'}
def build(row,template,count):
 bundle=row['evidence'];reject_gt(bundle)
 if digest(bundle)!=row['evidence_sha256']:raise ValueError('Evidence changed')
 prompts=dict(row['prompts']);body=json.dumps(bundle,ensure_ascii=False,sort_keys=True)
 for name,instruction in EXTRA.items():prompts[name]=template.wrap(body+'\n\n'+instruction)
 if any(count(v)>4096 for v in prompts.values()):raise ValueError('Common cap')
 for arm in ('v1-A','v1-B'):
  if sha(prompts[arm])!=row['prompt_sha256'][arm]:raise ValueError('Frozen prompt changed')
 return prompts

def main():
 source=PrivateAudit('.local_artifacts/narrative_v1').read(PIN)
 template=FrozenPromptTemplate.from_receipt('.local_artifacts/frozen/preparation_receipt.json')
 references={arm:read_pinned_json('.local_artifacts/authentic/'+name,PINS[name]) for arm,name in [('B1','b1_prompts.json'),('v0','narrative_prompts.json')]}
 framed=_local_counter('.local_artifacts/tokenizer_cache');count=lambda s:framed(s)-64
 requests=[];stats={};provisional=dict(endpoint='https://api.gapgpt.app/v1/chat/completions',model='gpt-6-luna',allowed_returned_models=['gpt-6-luna','gpt-6-luna-2026-09-22'],temperature=0.7,n=1,max_tokens=4096,max_input_tokens=32768,availability='UNVERIFIED_CURRENT',pricing='OWNER_HISTORICAL_UNVERIFIED',spending_cap='NOT_APPROVED')
 for row in source['rows']:
  node=row['node_id'];arms=build(row,template,count)
  for arm,reference in references.items():arms[arm]=reference['prompts_by_target_id'][str(node)]
  for arm,prompt in arms.items():
   tokens=count(prompt);s=stats.setdefault(arm,dict(calls=0,input_prompt_tokens=0,max_prompt_tokens=0))
   s['calls']+=3;s['input_prompt_tokens']+=3*tokens;s['max_prompt_tokens']=max(s['max_prompt_tokens'],tokens)
   for sample in range(3):
    entry=dict(arm=arm,node_id=node,sample_index=sample,prompt=prompt,prompt_sha256=sha(prompt),tokens=tokens,configuration=provisional,status='DRAFT_NOT_AUTHORIZED')
    entry['draft_identity']=digest(entry);requests.append(entry)
 for s in stats.values():
  s['estimated_input_usd_at_unverified_rate']=str(Decimal(s['input_prompt_tokens']+128*s['calls'])*Decimal('.10')/1000000)
  s['scenario_output_512_usd']=str(Decimal(s['calls']*512)*Decimal('.50')/1000000)
  s['declared_reservation_usd']=str(Decimal(s['calls'])*(Decimal(32768)*Decimal('.10')+Decimal(4096)*Decimal('.50'))/1000000)
 result=dict(schema='sara.prompt.six_arm.preflight.v1',source_freeze_sha256=PIN,instructions=EXTRA,requests=requests,configuration=provisional,per_arm=stats,
  stage_b='2 targets by SHA256 six-arm-smoke-v1|node_id order; 6 arms x3 samples =36 calls included in2520 total',
  primary='v1-B minus v1-A top1 all140 paired accuracy after independent prediction freeze',
  execution='BLOCKED_MODEL_PRICING_AND_SPENDING_APPROVAL',training_runs=0,provider_calls=0)
 store=PrivateAudit('.local_artifacts/narrative_six_arm');pin=store.write(result);assert store.read(pin)==result
 public={k:v for k,v in result.items() if k not in ('requests','instructions')};public['manifest_sha256']=pin
 Path('reports/narrative_six_arm_preflight.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(manifest_sha256=pin,requests=len(requests),per_arm=stats)))
if __name__=='__main__':main()
