"""Frozen lexical-description and confidence-margin hypotheses. No GT imports."""
import re
from pathlib import Path
from ..io.project import load_project_inputs
from ..sara3.audit import PrivateAudit
from ..sara3.selection import select_router
from ..sara3.atlas import ATLAS

VERSION = "atlas_confidence.v1"
STOP = set("learning using with and their through the or of in by and".split())

def tokens(text):
    return set(re.findall("[a-z]+", text.lower())) - STOP

def risk(pair):
    words = tokens(pair.text)
    scores = []
    for entry in ATLAS:
        vocabulary = tokens(entry.definition) | set(entry.keywords)
        scores.append(len(words & vocabulary) / (len(vocabulary)*max(1,len(words)))**0.5)
    top = max(scores)
    if not top:
        return float(not pair.agrees)
    candidate = (scores[pair.b1.class_index]+scores[pair.narrative_v0.class_index])/2
    return int(not pair.agrees) + 1-candidate/top + sorted(scores)[-2]/top

def vote(pair, margin):
    a,b = pair.b1,pair.narrative_v0
    if pair.agrees:
        return a.class_index if min(a.confidence,b.confidence)>=80 else None
    if margin and max(a.confidence,b.confidence)>=90 and abs(a.confidence-b.confidence)>=margin:
        return max((a,b),key=lambda x:x.confidence).class_index
    return None

def main():
    import hashlib
    inputs=load_project_inputs('.local_artifacts/frozen','.local_artifacts/authentic')
    pairs=inputs.pairs
    ranks={r:list(select_router(pairs,37,r)) for r in ('r0','r1_v1','r1_v2')}
    ranks['description_cosine']= [p.node_id for p in sorted(pairs,key=lambda p:(-risk(p),p.node_id))[:37]]
    rows=[[p.node_id,p.b1.class_index,p.narrative_v0.class_index,*[vote(p,m) for m in (0,10,20)]] for p in pairs]
    print(PrivateAudit('.local_artifacts/atlas_confidence_v1').write(dict(version=VERSION,code=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows,ranks=ranks)))

if __name__=='__main__':main()
