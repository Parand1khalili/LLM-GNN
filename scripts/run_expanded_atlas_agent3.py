"""Owner-authorized frozen Expanded Atlas execution; hidden terminal key entry."""
import getpass
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from llmgnn_sara.io.project import load_project_inputs
from llmgnn_sara.sara3 import atlas,r1_candidate
from llmgnn_sara.sara3.audit import PrivateAudit
from llmgnn_sara.sara3.gateway_run import gateway_run,approval_template,OWNER_PERMISSIONS
from llmgnn_sara.sara3.experiment import digest

def main():
    if '--inspect-only' in sys.argv[1:]:
        journal=PrivateAudit('.local_artifacts/expanded_atlas_agent3_v1/journal')
        summaries=[]
        for path in journal.root.glob('*.json'):
            value=journal.read(path.stem)
            if value.get('schema')=='sara.runner.gapgpt_transport.v1':
                summaries.append((path.stem,value))
        if len(summaries)!=1:
            raise RuntimeError('Expected one immutable summary; manual audit required')
        sha,value=summaries[0]
        print(json.dumps({k:value.get(k) for k in ('status','attempted_calls','blind_completed','comparison_completed','journal_states','rejection_codes','usage','estimated_cost_usd')}))
        print('PRIVATE_SUMMARY_SHA256',sha)
        return
    if Path('.local_artifacts/expanded_atlas_agent3_v1/journal/fixture_journal.sqlite').exists():
        raise RuntimeError('Existing execution requires --inspect-only; no automatic restart')
    frozen=PrivateAudit('.local_artifacts/expanded_atlas_ablation').read('6b624adac49e9a8e3a78de6d7628e4fc1b654b21b5307a33ebd9b5ef4a007fe0')
    inputs=load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic')
    entries=tuple(replace(c,keywords=tuple(v)) for c,v in zip(atlas.ATLAS,frozen['expanded']['vocab']))
    cfg=json.loads(Path('configs/gapgpt_rich_v2_output4096_proposed.json').read_text())
    cfg['max_spend_usd']='1.00'
    with patch.object(atlas,'ATLAS',entries):
        assert list(r1_candidate.route_r1_candidate(inputs.pairs))==frozen['expanded']['ids']
        approval=approval_template(inputs,'r1_v1',37,'sensitivity',cfg)
        for field in OWNER_PERMISSIONS:approval[field]=True
        print('Expanded Atlas |37 blind|max37 conditional|GapGPT|gpt-6-luna|max USD1.00')
        print('Pricing and retention UNVERIFIED; owner accepted risk. No retries of uncertain intents.')
        key=os.environ.get('GAPGPT_API_KEY')
        if not key:
            if not sys.stdin.isatty():raise RuntimeError('Interactive owner terminal required')
            key=getpass.getpass('GapGPT API key (hidden): ')
        if not key:raise RuntimeError('Credential unavailable')
        result=gateway_run(inputs,'.local_artifacts/expanded_atlas_agent3_v1',router='r1_v1',budget=37,cohort='sensitivity',config=cfg,fake=False,approval=approval,key=key)
        print('PRIVATE_SUMMARY_SHA256',result['private_summary_sha256'])

if __name__=='__main__':main()

